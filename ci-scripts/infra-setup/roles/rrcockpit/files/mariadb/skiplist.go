package main

import (
    "encoding/csv"
    "encoding/json"
    "fmt"
    "io/ioutil"
    "log"
    "net/http"
    "os"
    "regexp"
    "strconv"
    "time"
    "flag"
)

const limit int = 10

type strslice string
type Timestamp time.Time

func (t *Timestamp) String() string{
  return time.Time(*t).String()
}

// Job - Basic struct returned by zuul api in json format
// Release of job, Status (PASSED|FAILED|SKIPPED), URL to logs
type Job struct {
    Release     strslice `json:"job_name"`
    Status      string `json:"result"`
    URL         string `json:"log_url"`
    Timestamp   string `json:"event_timestamp"`
}

type Channel struct {
    Release string
    Logs string
}

type Result struct {
    Testname string
    Testresult string
    Release string
}

func main() {
  var skiplist, skip_stats bool

  flag.BoolVar(&skip_stats, "Stats", false, "Print skiplist stats")
  flag.BoolVar(&skiplist, "Skiplist", false, "Print skiplist")

  flag.Parse()
  if (skip_stats){
    jobs := getJobs("")
    tests := make(map[string]map[string][]int)
    collectData(jobs, tests)
    reportCSV(tests)
  }
  if (skiplist) {
    checkPassedTests()
  }
}

func collectData(jobs []Job, tests map[string]map[string][]int) {
    ch := make(chan Channel)
    size := 0
    for _, job := range jobs {
        if job.Status != "SKIPPED" {
            go fetchLogs(job.Release, job.URL, ch)
            size++
        }
    }

    for i := 0; i < size; i++ {
        results := parseResults(ch)
        for _, result := range results {
      testname, testresult, release := result.Testname, result.Testresult, result.Release

            if tests[release] == nil {
                tests[release] = make(map[string][]int)
            }
            if tests[release][testname] == nil {
                    tests[release][testname] = []int{}
            }

            result := tests[release][testname]
            if testresult == "FAILED" {
                result = append(result, 0)
            } else {
                result = append(result, 1)
            }

            tests[release][testname] = result
        }
    }
}

func reportCSV(tests map[string]map[string][]int) {

    w := csv.NewWriter(os.Stdout)

    for release, results := range tests {
        for key, value := range results {
            passing, failing, lastPassing, lastFailing := sum_results(value)
            record := []string{"0", release, key, passing, failing, lastPassing, lastFailing}

            if err := w.Write(record); err != nil {
                log.Fatalln("Error while writing record to csv: ", err)
            }
        }
    }

    w.Flush()
    if err := w.Error(); err != nil {
        log.Fatal(err)
    }
}

func Reverse(input []int) []int {
    var output []int
    for i := len(input) - 1; i >= 0; i-- {
        output = append(output, input[i])
    }
    return output
}

func sum_results(results []int) (string, string, string, string) {
    sum := 0
    passing := 0
    lastPassing := 0
    lastFailing := 0
    // NOTE(dasm): Reverse array and count last x indices
    for index, value := range Reverse(results) {
        passing += value
        sum += 1
        if index < limit {
            lastPassing += value
            if value == 0 {
                lastFailing += 1
            }
        }
    }
    failing := sum - passing
    return strconv.Itoa(passing), strconv.Itoa(failing), strconv.Itoa(lastPassing), strconv.Itoa(lastFailing)
}

func fetchLogs(release strslice, url string, ch chan Channel) {
    path := "logs/undercloud/var/log/tempest/tempest_run.log.txt.gz"
    fullURL := fmt.Sprintf("%s%s", url, path)

    response, err := http.Get(fullURL)
    if err != nil {
        channel := Channel{string(release), fmt.Sprintf("Error in get %s: %v", fullURL, err)}
        ch <- channel
        return
    }

    if response.StatusCode == 404 {
        // NOTE(dasm): Tempest didn't start
        channel := Channel{string(release), fmt.Sprintf("Error in get %s: %v", fullURL, err)}
        ch <- channel
        return
    }

    data, err := ioutil.ReadAll(response.Body)
    if err != nil {
        channel := Channel{string(release), fmt.Sprintf("Error while reading data from %s: %v", fullURL, err)}
        ch <- channel
        return
    }

    channel := Channel{string(release), string(data)}
    ch <- channel
}

func getJobs(url string) []Job {
  if url == "" {
    url = "https://review.rdoproject.org/zuul/api/builds?pipeline=openstack-periodic-weekend&limit=150"
  }
    var builds []Job
    response, err := http.Get(url)
    if err != nil {
        log.Fatalf("The HTTP request failed with error %s\n", err)
    } else {
        data, _ := ioutil.ReadAll(response.Body)
        if err := json.Unmarshal(data, &builds); err != nil {
            log.Printf("The Unmarshal failed with error %s\n", err)
        }
    }
    return builds
}

func parseResults(ch chan Channel) []Result {
    r, _ := regexp.Compile(`\{\d\}\s(setUpClass|tearDownClass\s)?\(?(?P<test>[^\(].*[^\)])(\))?\s\[\d.*\.\d.*\]\s...\s(?P<status>ok|FAILED)`)
    var result []Result

    channel := <-ch
    data, release := channel.Logs, channel.Release

    for _, matches := range r.FindAllStringSubmatch(data, -1) {
        result = append(result, Result{matches[2], matches[4], release})
    }
    return result
}
