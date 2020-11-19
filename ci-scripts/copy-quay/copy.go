package main

import (
	"fmt"
	"os"

	"github.com/containers/image/v5/copy"
	"github.com/containers/image/v5/manifest"
	"github.com/containers/image/v5/transports/alltransports"
	"github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

type copyOptions struct {
	global *globalOptions
}

var optsCopy = &copyOptions{}

func copyCmd(global *globalOptions) *cobra.Command {
	optsCopy.global = global

	cmd := &cobra.Command{
		Use:   "copy [CONTAINER NAME]",
		Short: "Copy images from source to destiny",
		RunE:  optsCopy.run,
	}

	return cmd
}

func (opts *copyOptions) run(cmd *cobra.Command, args []string) error {
	if len(args) > 0 {
		for _, image := range args {
			from := fmt.Sprintf("docker://%s/%s/%s:%s", opts.global.pullRegistry, opts.global.fromNamespace, image, opts.global.tag)
			to := fmt.Sprintf("docker://%s/%s/%s:%s", opts.global.pushRegistry, opts.global.toNamespace, image, opts.global.tag)
			if _, err := copyImage(from, to); err != nil {
				logrus.Errorln("Failed to copy container %s: %v", image, err)
			}
		}
	} else {
		image := getLatestGoodBuildURL(opts.global.job, opts.global)
		data := fetchLogs(image)
		res := parseLog(data)
		repositories, err := listRepositories(opts.global.toNamespace)
		if err != nil {
			logrus.Error("Failed to fetch list of repositories ", err)
		}
		for _, res := range res {
			logrus.Info(fmt.Sprintf("Copying image %s/%s", opts.global.toNamespace, res[0]))
			if !repoExists(res[0], repositories) {
				_, err := createNewRepository(opts.global.toNamespace, res[0])
				if err != nil {
					logrus.Errorln("Failed to create repository: ", err)
				}
			}
			from := fmt.Sprintf("docker://%s/%s/%s:current-tripleo", opts.global.pullRegistry, opts.global.fromNamespace, res[0])
			to := fmt.Sprintf("docker://%s/%s/%s:%s", opts.global.pushRegistry, opts.global.toNamespace, res[0], res[1])
			_, err := copyImage(from, to)
			if err != nil {
				logrus.Errorln("Failed to copy container image: ", err)
			}
			sha, err := getImageManifest(opts.global.toNamespace, res[0])
			if err != nil {
				logrus.Errorln("Unable to get image manifest: ", err)
			}
			tagImage(opts.global.toNamespace, res[0], "current-tripleo", sha)
		}
	}

	return nil
}

func copyImage(from, to string) (string, error) {

	logrus.Debug(fmt.Sprintf("Copying container image %s to %s", from, to))
	srcRef, err := alltransports.ParseImageName(from)
	if err != nil {
		return "", fmt.Errorf("Failed to parse image %s to be pulled from: %v", from, err)
	}

	destRef, err := alltransports.ParseImageName(to)
	if err != nil {
		return "", fmt.Errorf("Failed to parse image %s to be pushed to: %v", to, err)
	}

	policyContext, err := optsCopy.global.getPolicyContext()
	if err != nil {
		return "", fmt.Errorf("Failed to get policy context: %v", err)
	}

	ctx, cancel := optsCopy.global.commandTimeoutContext()
	defer cancel()

	sourceCtx := optsCopy.global.newSystemContext()
	destinationCtx := optsCopy.global.newImageDestSystemContext()

	man, err := copy.Image(ctx, policyContext, destRef, srcRef, &copy.Options{
		RemoveSignatures:      true,
		SignBy:                "",
		ReportWriter:          os.Stdin,
		SourceCtx:             sourceCtx,
		DestinationCtx:        destinationCtx,
		ForceManifestMIMEType: manifest.DockerV2Schema2MediaType,
		ImageListSelection:    copy.CopySystemImage,
	})
	if err != nil {
		return "", fmt.Errorf("Error in copy the image: %v", err)
	}
	logrus.Debugln("Image copied successfully")

	return string(man), nil
}
