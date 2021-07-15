package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"html/template"
	"io/ioutil"
	"net/http"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
)

// Build - Basic struct returned by zuul api in json format
type Build struct {
	Status string `json:"result"`
	URL    string `json:"log_url"`
}

func getJobPerRelease(release string) string {
	var jobList = map[string]string{
		"master":   "periodic-tripleo-ci-build-containers-ubi-8-push",
		"queens":   "https://trunk.rdoproject.org/api-centos-queens",
		"rocky":    "periodic-tripleo-centos-7-rocky-containers-build-push",
		"stein":    "periodic-tripleo-centos-7-stein-containers-build-push",
		"train":    "periodic-tripleo-centos-7-train-containers-build-push",
		"train8":   "periodic-tripleo-ci-build-containers-ubi-8-push-train",
		"ussuri":   "periodic-tripleo-ci-build-containers-ubi-8-push-ussuri",
		"victoria": "periodic-tripleo-ci-build-containers-ubi-8-push-victoria",
		"wallaby":  "periodic-tripleo-ci-build-containers-ubi-8-push-wallaby",
	}

	return jobList[release]
}

func writeHTLMReport(success []string, failed []string, hash string, output string) {

	var reportTemplate = template.Must(template.New("report").Parse(`
	<!DOCTYPE html>
	<html>
	<head>
	<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css"
	      integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T"
		  crossorigin="anonymous">
	<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js"
	        integrity="sha384-JjSmVgyd0p3pXB1rRibZUAYoIIy6OrQ6VrjIEaFf/nJGzIxFDsf4x0xIM+B07jRM"
			crossorigin="anonymous">
	</script>
	</head>
	<body>
	<h2>Report latest containers</h2>
	<h3>Latest hash: {{.Hash}}</h3>
	<h3>Date: {{.Today.Format "01-02-2006 15:04"}}</h3>
	<h4>Failing: {{.Failing}}</h4>
	<h4>Passing: {{.Passing}}</h4>
	<table class="table table-hover">
	<thead>
		<tr>
		<th>Container Name</th>
		<th>Status</th>
		</tr>
	</thead>
	<tbody>
	{{range .Items}}
		{{ if eq .ContainerStatus "SUCCESS" }}
		<tr class="table-success">
		{{ else }}
		<tr class="table-danger">
		{{ end }}
		<td>{{.ContainerName}}</td>
		<td>{{.ContainerStatus}}</td>
		</tr>
		<tr>
	{{end}}
	</tbody>
	</table>
	</body>
	</html>
	`))

	type Containers struct {
		ContainerName   string
		ContainerStatus string
	}

	type Data struct {
		Items   []*Containers
		Hash    string
		Today   time.Time
		Passing int
		Failing int
	}

	data := new(Data)
	data.Hash = hash
	data.Today = time.Now()
	data.Passing = len(success)
	data.Failing = len(failed)

	for _, container := range success {
		item := new(Containers)
		item.ContainerName = container
		item.ContainerStatus = "SUCCESS"
		data.Items = append(data.Items, item)
	}
	for _, container := range failed {
		item := new(Containers)
		item.ContainerName = container
		item.ContainerStatus = "FAILURE"
		data.Items = append(data.Items, item)
	}

	file, err := os.Create(output)
	if err != nil {
		logrus.Errorln("Failed to create HTML report file")
	}
	writer := bufio.NewWriter(file)
	if err := reportTemplate.Execute(writer, data); err != nil {
		writer.Flush()
		logrus.Fatal(err)
	}
	writer.Flush()
}

func getLatestGoodBuildURL(jobName string, opts *globalOptions) string {

	url := fmt.Sprintf("%sbuilds?job_name=%s", opts.zuulAPI, jobName)
	response, err := http.Get(url)
	defer response.Body.Close()
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

func _fetch(url string) (string, error) {
	response, err := http.Get(url)
	defer response.Body.Close()
	if err != nil {
		logrus.Errorln("The HTTP request failed with error ", err)
		return "", err
	}
	if response.StatusCode == 404 {
		msg := fmt.Sprintf("URL not found: %s", url)
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

func fetchLogs(url string) string {
	// There are three different places where we can get the list of
	// containers...
	path := fmt.Sprintf("%slogs/containers-successfully-built.log", url)
	data, _ := _fetch(path)

	if data == "" {
		path := fmt.Sprintf("%slogs/containers-built.log", url)
		data, _ = _fetch(path)
	}

	if data == "" {
		path := fmt.Sprintf("%sjob-output.txt", url)
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

	type DlrnAPIResponse struct {
		PromoteName   string `json:"promote_name"`
		RepoHash      string `json:"repo_hash"`
		AggregateHash string `json:"aggregate_hash"`
		CommitHash    string `json:"commit_hash"`
	}

	var returnAPI []DlrnAPIResponse

	apiEndpoint := "api/promotions?promote_name=current-tripleo&limit=1"
	apiURL := fmt.Sprintf("%s/%s", api, apiEndpoint)

	response, err := http.Get(apiURL)
	defer response.Body.Close()
	if err != nil {
		logrus.Errorln("The HTTP request failed with error ", err)
	} else {
		data, _ := ioutil.ReadAll(response.Body)
		if err := json.Unmarshal(data, &returnAPI); err != nil {
			logrus.Errorln("The unmarshal failed with error ", err)
		}
	}
	if len(returnAPI) > 0 {
		if returnAPI[0].AggregateHash != "" {
			return returnAPI[0].AggregateHash
		}
		return returnAPI[0].RepoHash
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
