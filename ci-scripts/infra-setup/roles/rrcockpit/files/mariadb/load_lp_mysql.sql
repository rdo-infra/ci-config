USE rrcockpit;
CREATE TABLE IF NOT EXISTS rr_bugs (
    id INT,
    status VARCHAR(255) NOT NULL,
    tag VARCHAR(255) NOT NULL,
    link VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (id)
);

TRUNCATE TABLE rr_bugs;

LOAD DATA LOCAL INFILE '/tmp/lp.csv' \n
INTO TABLE rr_bugs \n
FIELDS TERMINATED BY ',' \n
LINES TERMINATED BY '\n';
