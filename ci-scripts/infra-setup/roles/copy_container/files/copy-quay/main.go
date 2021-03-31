package main

import (
	"context"

	"github.com/containers/image/v5/signature"
	"github.com/containers/image/v5/types"
	"github.com/containers/storage/pkg/reexec"
	"github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

type globalOptions struct {
	zuulAPI       string
	pullRegistry  string
	pushRegistry  string
	fromNamespace string
	toNamespace   string
	hash          string
	pushHash      string
	forceTag      string
	job           string
	token         string
    release       string
	debug         bool
}

var opts = &globalOptions{}

func createApp() (*cobra.Command, *globalOptions) {

	rootCommand := &cobra.Command{
		Use:  "copy-quay",
		Long: "Copy a container from one location to another",
		PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
			return opts.before(cmd)
		},
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	rootCommand.PersistentFlags().StringVar(&opts.zuulAPI, "zuul-api", "https://review.rdoproject.org/zuul/api/", "Zuul api endpoint")
	rootCommand.PersistentFlags().StringVar(&opts.pullRegistry, "pull-registry", "trunk.registry.rdoproject.org", "Registry to pull images from")
	rootCommand.PersistentFlags().StringVar(&opts.pushRegistry, "push-registry", "quay.io", "Registry to push images to")
	rootCommand.PersistentFlags().StringVar(&opts.fromNamespace, "from-namespace", "tripleomaster", "Namespace of pushed image")
	rootCommand.PersistentFlags().StringVar(&opts.toNamespace, "to-namespace", "tripleomaster", "Namespace of pushed image")
	rootCommand.PersistentFlags().StringVar(&opts.hash, "hash", "", "Hash to be pulled/pushed")
	rootCommand.PersistentFlags().StringVar(&opts.pushHash, "push-hash", "", "Hash to be pulled/pushed")
	rootCommand.PersistentFlags().StringVar(&opts.token, "token", "", "Token to use with quay api")
	rootCommand.PersistentFlags().BoolVar(&opts.debug, "debug", false, "Enable debug output")
	rootCommand.PersistentFlags().StringVar(&opts.job, "job", "", "Job to collect the list of containers")
    rootCommand.PersistentFlags().StringVar(&opts.release, "release", "master", "Release")
	rootCommand.AddCommand(copyCmd(opts))
    rootCommand.AddCommand(tagCmd(opts))
	return rootCommand, opts
}

func (opts *globalOptions) before(cmd *cobra.Command) error {
	if opts.debug {
		logrus.SetLevel(logrus.DebugLevel)
	}
	return nil
}
func (opts *globalOptions) newImageDestSystemContext() *types.SystemContext {
	ctx := opts.newSystemContext()
	ctx.DirForceCompress = false
	ctx.OCIAcceptUncompressedLayers = false

	return ctx
}

func (opts *globalOptions) newSystemContext() *types.SystemContext {
	ctx := &types.SystemContext{
		RegistriesDirPath:        "",
		ArchitectureChoice:       "",
		OSChoice:                 "",
		VariantChoice:            "",
		SystemRegistriesConfPath: "",
		BigFilesTemporaryDir:     "",
	}
	return ctx
}

func (opts *globalOptions) getPolicyContext() (*signature.PolicyContext, error) {
	var policy *signature.Policy // This could be cached across calls in opts.
	var err error
	policy, err = signature.DefaultPolicy(nil)
	if err != nil {
		return nil, err
	}
	return signature.NewPolicyContext(policy)
}

func (opts *globalOptions) commandTimeoutContext() (context.Context, context.CancelFunc) {
	ctx := context.Background()
	var cancel context.CancelFunc = func() {}
	return ctx, cancel
}

func main() {

	if reexec.Init() {
		return
	}
	rootCmd, _ := createApp()
	if err := rootCmd.Execute(); err != nil {
		logrus.Fatal(err)
	}
}
