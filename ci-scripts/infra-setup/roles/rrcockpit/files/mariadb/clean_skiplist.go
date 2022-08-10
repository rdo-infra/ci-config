package main

import (
  "fmt"
  "net/http"
  "io"
  "gopkg.in/yaml.v3"
)

type StructRelease struct{
  Name         string   `yaml:"name"`
  Reason       string   `yaml:"reason"`
  LP           string   `yaml:"lp"`
  Installers   []string `yaml:"installers"`
}


type StructJobs struct{
  Jobs     []string //`yaml:"jobs"`
}

type StructSkiplist struct{
  Test           string        `yaml:"test"`
  Deployment   []string        `yaml:"deployment"`
  Release      []StructRelease `yaml:"releases"`
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


func getJobTests() map[string]map[string][]int {
  job_tests := make(map[string]map[string][]int)
  jobs := getWeekendPipeline("")
  collectData(jobs, job_tests)
  return job_tests
}


func checkPassedTests(){
  skiplist := getSkiplistTests()
  jobtests := getJobTests()

  job_test_map := make(map[string][]string)

  for key, value := range jobtests {
    for testname, _ := range value {
      if job_test_map[key] == nil {
        job_test_map[key] = []string{}
      }
      if job_test_map[key] != nil {
        tests := job_test_map[key]
        tests = append(tests, testname)
        job_test_map[key] = tests
      }
    }
  }

  passed_tests := make(map[string][]string)
  for key, value := range job_test_map{
    for _, s_test := range skiplist {
      if isExists(value, s_test){
        if passed_tests[s_test] == nil {
          passed_tests[s_test] = []string{}
        }
        if passed_tests[s_test] != nil {
          tmp_var := passed_tests[s_test]
          tmp_var = append(tmp_var, key)
          passed_tests[s_test] = tmp_var
        }
      }
    }
  }

  fmt.Println("Skiplist Test: ")
  for key, value := range passed_tests {
    if value != nil {
      fmt.Printf("\n  - %s \n    Jobs:", key)
      for _, val := range value{
        fmt.Printf("\n       - %s ", val)
      }
    } else {
      fmt.Println("No tests passed.")
    }
  }
}
