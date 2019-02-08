USE rrcockpit;

CREATE TABLE IF NOT EXISTS noop_builds (
    branch VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,
    job VARCHAR(255) NOT NULL,
    log_url VARCHAR(255) NOT NULL,
    result VARCHAR(255) NOT NULL,
    success INT,
    ts VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (branch, type, job)
);

TRUNCATE TABLE noop_builds;

LOAD DATA LOCAL INFILE '/tmp/noop.csv' \n
INTO TABLE noop_builds\n
FIELDS TERMINATED BY ',' \n
LINES TERMINATED BY '\n';
