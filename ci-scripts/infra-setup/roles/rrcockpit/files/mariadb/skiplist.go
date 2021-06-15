package main

import (
    "encoding/csv"
    "encoding/json"
    "flag"
    "fmt"
    "io/ioutil"
    "log"
    "net/http"
    "os"
    "regexp"
    "strconv"

    "github.com/jedib0t/go-pretty/table"
    "gopkg.in/yaml.v2"
)

// SkipTests - Struct returned by the yaml file containing the skipped
// tests
type SkipTests struct {
    KnownFailures []struct {
        Test string `yaml:"test"`
    } `yaml:"known_failures"`
}

// ListJobs is the struct to return the list of jobs you want to check
type ListJobs []string

func (i *ListJobs) String() string {
    return "List of jobs"
}

// Set the value parsed by the flags parser
func (i *ListJobs) Set(value string) error {
    *i = append(*i, value)
    return nil
}

// Builds - Basic struct returned by zuul api in json format
// We don't need all the values, just these two,
// Status and the URL
type Builds struct {
    Status string `json:"result"`
    URL    string `json:"log_url"`
}

// TestResult - This is the result of the test, wether is
// failing or passing, it acts as a counter
type TestResult struct {
    Passing int
    Failing int
}

var jobs ListJobs
var is_csv bool
var release string

func parseArgs() {
        // Default job values
    jobs = ListJobs{}

    flag.Var(&jobs, "job", "List of jobs to collect tempest result")
    flag.BoolVar(&is_csv, "csv", false, "Show csv output")
    flag.StringVar(&release, "release", "master", "Release")
    flag.Parse()
}

func main() {

    parseArgs()

    tests := make(map[string]*TestResult)
    lastTen := make(map[string]*TestResult)
    builds := make(map[string][]Builds)

    var sumBuilds, lastTenBuilds []Builds

    for _, job := range jobs {
        jobSlice := 10
        buildsJob := getBuilds(job)
        builds[job] = buildsJob
        if len(buildsJob) < 10 {
            jobSlice = len(buildsJob) - 1
        }
        lastTenBuilds = append(lastTenBuilds, buildsJob[:jobSlice]...)
        sumBuilds = append(sumBuilds, buildsJob...)
    }

    collectData(sumBuilds, tests)
    collectData(lastTenBuilds, lastTen)

    if is_csv {
        reportCSV(tests, lastTen)
    } else {
        reportTable(tests, lastTen)
    }
}

func loadYaml(yamlPath string) (*SkipTests, error) {
    skipTests := &SkipTests{}

    file, err := os.Open(yamlPath)
    if err != nil {
        return nil, err
    }

    defer file.Close()

    d := yaml.NewDecoder(file)
    if err := d.Decode(&skipTests); err != nil {
        return nil, err
    }
    return skipTests, nil
}

func collectData(builds []Builds, tests map[string]*TestResult) {
    ch := make(chan string)
    size := 0
    for _, build := range builds {
        if build.Status != "SKIPPED" {
            go fetchLogs(build.URL, ch)
            size++
        }
    }

    for i := 0; i < size; i++ {
        results := parseResults(ch)
        for _, result := range results {
            if tests[result[0]] == nil {
                tests[result[0]] = &TestResult{0, 0}
            }
            if result[1] == "FAILED" {
                tests[result[0]].Failing++
            } else {
                tests[result[0]].Passing++
            }
        }
    }
}

func reportCSV(results, lastTen map[string]*TestResult) {

    w := csv.NewWriter(os.Stdout)

    for key, value := range results {
        lastTenPassing := 0
        lastTenFailing := 0
        if lastTen[key] != nil {
            lastTenPassing = lastTen[key].Passing
            lastTenFailing = lastTen[key].Failing
        }

        record := []string{"0", release, key,
                           strconv.Itoa(value.Passing),
                           strconv.Itoa(value.Failing),
                           strconv.Itoa(lastTenPassing),
                           strconv.Itoa(lastTenFailing)}

        if err := w.Write(record); err != nil {
            log.Fatalln("Error while writing record to csv: ", err)
        }
    }

    w.Flush()
    if err := w.Error(); err != nil {
        log.Fatal(err)
    }
}

func reportTable(results, lastTen map[string]*TestResult) {
    t := table.NewWriter()
    t.SetOutputMirror(os.Stdout)
    t.AppendHeader(table.Row{"Test name", "Passing", "Failing", "Last 10 passing", "Last 10 failing"})

    for key, value := range results {
        if lastTen[key] == nil {
            lastTen[key] = &TestResult{}
        }
        t.AppendRow([]interface{}{key, value.Passing, value.Failing, lastTen[key].Passing, lastTen[key].Failing})
    }

    t.Render()
}

func fetchLogs(url string, ch chan<- string) {
    path := "logs/undercloud/var/log/tempest/tempest_run.log.txt.gz"
    fullURL := fmt.Sprintf("%s%s", url, path)

    response, err := http.Get(fullURL)
    if err != nil {
        ch <- fmt.Sprintf("Error in get %s: %v", fullURL, err)
        return
    }

    if response.StatusCode == 404 {
        // Some releases still using validate-tempest
        path := "logs/undercloud/home/zuul/tempest.log.txt.gz"
        fullURL := fmt.Sprintf("%s%s", url, path)
        response, err = http.Get(fullURL)
        if err != nil {
            ch <- fmt.Sprintf("Error in get %s: %v", fullURL, err)
            return
        }
    }

    data, err := ioutil.ReadAll(response.Body)
    if err != nil {
        ch <- fmt.Sprintf("Error while reading data from %s: %v", fullURL, err)
        return
    }

    ch <- string(data)
}

func getBuilds(jobName string) []Builds {
    var url = "https://review.rdoproject.org/zuul/api/builds?job_name=%s"
    var builds []Builds
    response, err := http.Get(fmt.Sprintf(url, jobName))
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

func parseResults(ch chan string) [][2]string {
    r, _ := regexp.Compile(`\{\d\}\s(setUpClass\s)?\(?(?P<test>[^\(].*[^\)])(\))?\s\[\d.*\.\d.*\]\s...\s(?P<status>ok|FAILED)`)
    var result [][2]string
    for _, matches := range r.FindAllStringSubmatch(<-ch, -1) {
        result = append(result, [2]string{matches[2], matches[4]})
    }
    return result
}
