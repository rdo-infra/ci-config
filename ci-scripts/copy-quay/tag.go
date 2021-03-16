package main

import (
	"fmt"

	"github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

type tagOptions struct {
    global *globalOptions
    tag string
    release string
    hash string
}


var optsTag = &tagOptions{}

func tagCmd(global *globalOptions) *cobra.Command {
    optsTag.global = global

    cmd := &cobra.Command{
        Use:   "tag [CONTAINER NAME]",
        Short: "Tag images",
        RunE: optsTag.run,
    }
    cmd.Flags().StringVar(&optsTag.tag, "tag", "current-tripleo", "Image tag name")
    cmd.Flags().StringVar(&optsTag.release, "api-release", "master", "DLRN api to be used")
    cmd.Flags().StringVar(&optsTag.hash, "force-hash", "", "Force an specific hash, overwriting delorean api")
    cmd.MarkFlagRequired("api-release")
    return cmd
}

func (opts *tagOptions) run(cmd *cobra.Command, args []string) error {

    var urlReleases = map[string]string {
        "master":    "https://trunk.rdoproject.org/api-centos8-master-uc",
        "queens":    "https://trunk.rdoproject.org/api-centos-queens",
        "rocky":     "https://trunk.rdoproject.org/api-centos-rocky",
        "stein":     "https://trunk.rdoproject.org/api-centos-stein",
        "train":     "https://trunk.rdoproject.org/api-centos-train",
        "train8":    "https://trunk.rdoproject.org/api-centos8-train",
        "ussuri":    "https://trunk.rdoproject.org/api-centos8-ussuri",
        "victoria" : "https://trunk.rdoproject.org/api-centos8-victoria",
    }
    urlApi := urlReleases[opts.release]
    if urlApi == "" {
        return fmt.Errorf("Invalid release. Valid values are: master, queens, rocky, stein, train, train8, ussuri and victoria")
    }

    var promoted_hash = ""
    if opts.hash != "" {
        logrus.Info("Overwriting promoted hash")
        promoted_hash = opts.hash
    } else {
        promoted_hash = getCurrentTripleoRepo(urlApi)
    }

    if len(args) > 0 {
        for _, image := range args {
            sha, err := getImageManifest(opts.global.toNamespace, image, promoted_hash)
            if err != nil {
                logrus.Errorln("Unable to get image manifest: ", err)
            } else {
                tagImage(opts.global.toNamespace, image, opts.tag, sha)
            }
        }
    } else {
        image := getLatestGoodBuildURL(opts.global.job, opts.global)
        data := fetchLogs(image)
        res := parseLog(data)

        for _, res := range res {
            sha, err := getImageManifest(opts.global.toNamespace, res[0], promoted_hash)
            if err != nil {
                logrus.Errorln("Unable to get image manifest: ", err)
            } else {
                tagImage(opts.global.toNamespace, res[0], opts.tag, sha)
            }
        }
    }
    return nil
}
