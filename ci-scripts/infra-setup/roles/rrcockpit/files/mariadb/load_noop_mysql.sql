USE rrcockpit;
CREATE TABLE IF NOT EXISTS noop_builds(
    type VARCHAR(255) NOT NULL,
    release VARCHAR(255) NOT NULL,
    job VARCHAR(255) NOT NULL,
    result VARCHAR(255) NOT NULL,
    description VARCHAR(255) NOT NULL,
    PRIMARY KEY (type, release, job)
);

TRUNCATE TABLE noop_builds;

LOAD DATA LOCAL INFILE '/tmp/noop.csv' \n
INTO TABLE noop_builds\n
FIELDS TERMINATED BY ',' \n
LINES TERMINATED BY '\n';
