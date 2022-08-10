package main

import (
	"fmt"
	"net/http"
	"io"
	"gopkg.in/yaml.v3"

)

type StructRelease struct{
	Name         string `yaml:"name"`
	Reason       string `yaml:"reason"`
	LP           string `yaml:"lp"`
	Installers   []string `yaml:"installers"`
}


type StructJobs struct{
	Jobs     []string //`yaml:"jobs"`
}

type StructSkiplist struct{
	Test           string    `yaml:"test"`
	Deployment   []string      `yaml:"deployment"`
	Release      []StructRelease     `yaml:"releases"`
	Jobs         StructJobs      `yaml:"jobs"`
}

func (sk StructSkiplist) PrintSkiplist(){

	fmt.Println(sk.Test)
	fmt.Println(sk.Deployment)
	fmt.Println(sk.Release)
	fmt.Println(sk.Jobs)
}

func isExists(s []string, value string) bool{
	for _, v := range s {
		if v == value {
			return true
		}
	}
	return false
}

func getAllTests(skiplist_struct map[string][]StructSkiplist) []string {
	var tests_list = []string{}

	for _, s := range skiplist_struct {
		for _, t := range s{
			if !isExists(tests_list, t.Test) {
				tests_list = append(tests_list, t.Test)
			}
		}
	}
	return tests_list
}


func getSkiplist(skiplist_struct map[string][]StructSkiplist) map[string][]StructSkiplist {

	var skiplist_url = "https://opendev.org/openstack/openstack-tempest-skiplist/raw/branch/master/roles/validate-tempest/vars/tempest_skip.yml"

	response, err := http.Get(skiplist_url)
	defer response.Body.Close()

	if err != nil {
		fmt.Println("Failed to fetch skiplist")
	} else {
		body, _ := io.ReadAll(response.Body)
		yaml.Unmarshal(body, &skiplist_struct)
	}
	return skiplist_struct
}


func getWeekendPipeline(url string) []Job {
	var zuul_weekend_pipeline string
	zuul_weekend_pipeline = url
	if url == ""{
		zuul_weekend_pipeline = "https://review.rdoproject.org/zuul/api/builds?pipeline=openstack-periodic-weekend&result=success"
	}

	var zuul_job_list = []Job{}
	zuul_job_list = getJobs(zuul_weekend_pipeline)

	return zuul_job_list
}


func getSkiplistTests() []string{
	skiplist_struct := make(map[string][]StructSkiplist)
	getSkiplist(skiplist_struct)
	tests_list := getAllTests(skiplist_struct)
	return tests_list
}

/*
func main(){
	skiplist_struct := make(map[string][]StructSkiplist)
	tests := make(map[string]map[string][]int)
	getSkiplist(skiplist_struct)
	tests_list := getSkiplistTests()
	fmt.Println(tests_list[0])

	jobs := getWeekendPipeline("")
	collectData(jobs, tests)
	fmt.Println(tests)


}
*/
