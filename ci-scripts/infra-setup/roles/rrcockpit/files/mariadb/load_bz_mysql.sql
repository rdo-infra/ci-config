USE rrcockpit;

CREATE TABLE IF NOT EXISTS rr_bz_bugs (
    id INT,
    status VARCHAR(255) NOT NULL,
    priority VARCHAR(255) NOT NULL,
    link VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (id)
);

TRUNCATE TABLE rr_bz_bugs;

LOAD DATA LOCAL INFILE '/tmp/bz.csv' \n
INTO TABLE rr_bz_bugs \n
FIELDS TERMINATED BY ',' \n
LINES TERMINATED BY '\n';
