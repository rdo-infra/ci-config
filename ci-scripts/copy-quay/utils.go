package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"regexp"

	"github.com/sirupsen/logrus"
)

// Build - Basic struct returned by zuul api in json format
type Build struct {
	Status string `json:"result"`
	URL    string `json:"log_url"`
}

func getLatestGoodBuildURL(jobName string, opts *globalOptions) string {
	url := fmt.Sprintf("%sbuilds?job_name=%s", opts.zuulAPI, opts.job)
	response, err := http.Get(url)
	var builds []Build

	if err != nil {
		logrus.Errorln("The HTTP request failed with error ", err)
	} else {
		data, _ := ioutil.ReadAll(response.Body)
		if err := json.Unmarshal(data, &builds); err != nil {
			logrus.Errorln("The unmarshal failed with error ", err)
		}
	}
	for _, build := range builds {
		if build.Status == "SUCCESS" {
			return build.URL
		}
	}
	return ""
}

func _fetch(URL string) (string, error) {
	response, err := http.Get(URL)
	if err != nil {
		logrus.Errorln("The HTTP request failed with error ", err)
		return "", err
	}
	if response.StatusCode == 404 {
		logrus.Errorln("URL not found: %s", URL)
		return "", fmt.Errorf("URL %s not found", URL)
	}
	data, err := ioutil.ReadAll(response.Body)
	if err != nil {
		logrus.Errorln("Failed to read Body content")
		return "", err
	}
	return string(data), nil
}

func fetchLogs(URL string) string {
	path := fmt.Sprintf("%slogs/containers-successfully-built.log", URL)
	data, _ := _fetch(path)

	if data == "" {
		path := fmt.Sprintf("%sjob-output.txt", URL)
		data, _ = _fetch(path)
	}
    logrus.Info("Fetching logs in ", path)
	return data
}

func repoExists(repoName string, repositories []Container) bool {
	for _, container := range repositories {
		if container.Name == repoName {
			return true
		}
	}
	return false
}
func parseLog(data string) [][2]string {
	r, _ := regexp.Compile(`(?m)item=docker push.*\/([\w-]+):([\w]+_[\w]+)`)
	var result [][2]string

	for _, matches := range r.FindAllStringSubmatch(data, -1) {
		result = append(result, [2]string{matches[1], matches[2]})
	}
	if len(result) == 0 {
		r, _ := regexp.Compile(`(?m)\/([\w-]+)\s+([\w_]+)`)

		for _, matches := range r.FindAllStringSubmatch(data, -1) {
			result = append(result, [2]string{matches[1], matches[2]})
		}
	}
	return result
}
