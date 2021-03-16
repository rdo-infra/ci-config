package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"regexp"
	"strings"

	"github.com/sirupsen/logrus"
)

// Build - Basic struct returned by zuul api in json format
type Build struct {
	Status string `json:"result"`
	URL    string `json:"log_url"`
}

func getJobPerRelease(release string) string {
    var jobList = map[string]string {
        "master":    "periodic-tripleo-ci-build-containers-ubi-8-push",
        "queens":    "https://trunk.rdoproject.org/api-centos-queens",
        "rocky":     "periodic-tripleo-centos-7-rocky-containers-build-push",
        "stein":     "periodic-tripleo-centos-7-stein-containers-build-push",
        "train":     "periodic-tripleo-centos-7-train-containers-build-push",
        "train8":    "periodic-tripleo-ci-build-containers-ubi-8-push-train",
        "ussuri":    "periodic-tripleo-ci-build-containers-ubi-8-push-ussuri",
        "victoria" : "periodic-tripleo-ci-build-containers-ubi-8-push-victoria",
    }

    return jobList[release]
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

func _fetch_(URL string) (string, error) {
    request, err := http.NewRequest(http.MethodGet, URL, nil)
    if err != nil {
        logrus.Errorln("The HTTP request failed with error ", err)
        return "", err
    }

    client := &http.Client{}
    response, err := client.Do(request)
    if err != nil {
        logrus.Errorln("Failed to get response from the HTTP request")
        return "", err
    }
    if response.StatusCode == 404 {
        msg := fmt.Sprintf("URL %s not found", URL)
        logrus.Errorln(msg)
        return "", fmt.Errorf(msg)
    }

	data, err := ioutil.ReadAll(response.Body)
	if err != nil {
		logrus.Errorln("Failed to read Body content")
		return "", err
	}
	return string(data), nil
}

func _fetch(URL string) (string, error) {
	response, err := http.Get(URL)
	if err != nil {
		logrus.Errorln("The HTTP request failed with error ", err)
		return "", err
	}
	if response.StatusCode == 404 {
        msg := fmt.Sprintf("URL not found: %s", URL)
		logrus.Errorln(msg)
		return "", fmt.Errorf(msg)
	}
	data, err := ioutil.ReadAll(response.Body)
	if err != nil {
		logrus.Errorln("Failed to read Body content")
		return "", err
	}
	return string(data), nil
}

func fetchLogs(URL string) string {
    // There are three different places where we can get the list of
    // containers...
	path := fmt.Sprintf("%slogs/containers-successfully-built.log", URL)
	data, _ := _fetch(path)

    if data == "" {
        path := fmt.Sprintf("%slogs/containers-built.log", URL)
        data , _ = _fetch(path)
    }

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

func getCurrentTripleoRepo(api string) string {

    type DlrnApiResponse struct {
        PromoteName   string `json:"promote_name"`
        RepoHash      string `json:"repo_hash"`
        AggregateHash string `json:"aggregate_hash"`
        CommitHash    string `json:"commit_hash"`
    }

    var returnApi []DlrnApiResponse

    apiEndpoint := "api/promotions?promote_name=current-tripleo&limit=1"
    apiUrl := fmt.Sprintf("%s/%s", api, apiEndpoint)

	response, err := http.Get(apiUrl)

	if err != nil {
		logrus.Errorln("The HTTP request failed with error ", err)
	} else {
		data, _ := ioutil.ReadAll(response.Body)
		if err := json.Unmarshal(data, &returnApi); err != nil {
			logrus.Errorln("The unmarshal failed with error ", err)
		}
	}
    if len(returnApi) > 0 {
        if returnApi[0].AggregateHash != "" {
            return returnApi[0].AggregateHash
        }
        return returnApi[0].RepoHash
    }

    return ""
}

func parseLog(data string) [][2]string {
	// r, _ := regexp.Compile(`(?m)item=docker push.*\/([\w-]+):([\w]+_[\w]+)`)
	r, _ := regexp.Compile(`(?m)primary \|\s(\w+)\: digest\:.*\n.*\n.*Tag w\/ arch suffix and push image: .*\/([\w-]+)`)
	var result [][2]string

	for _, matches := range r.FindAllStringSubmatch(data, -1) {
		if strings.Contains(matches[1], "x86_64") {
			result = append(result, [2]string{matches[2], matches[1][:len(matches[1])-7]})
		}
        // result = append(result, [2]string{matches[2], matches[1]})
	}
	if len(result) == 0 {
		r, _ := regexp.Compile(`(?m)\/([\w-]+)\s+([\w_]+)`)

		for _, matches := range r.FindAllStringSubmatch(data, -1) {
			result = append(result, [2]string{matches[1], matches[2]})
		}
	}
	return result
}
