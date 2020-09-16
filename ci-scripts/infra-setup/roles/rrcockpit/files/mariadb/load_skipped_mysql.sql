USE rrcockpit;

CREATE TABLE IF NOT EXISTS rr_skipped_list(
    id MEDIUMINT  NOT NULL AUTO_INCREMENT,
    Branch VARCHAR(255) NOT NULL,
    Testname VARCHAR(255) NOT NULL,
    Passing INT NOT NULL,
    Failing INT NOT NULL,
    Last_Ten_Passing INT NOT NULL,
    Last_Ten_Failing INT NOT NULL,
    PRIMARY KEY (id)
);

TRUNCATE TABLE rr_skipped_list;

LOAD DATA LOCAL INFILE '/tmp/skipped.csv' \n
INTO TABLE rr_skipped_list\n
FIELDS TERMINATED BY ',' \n
LINES TERMINATED BY '\n';
