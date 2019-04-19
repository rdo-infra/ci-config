USE rrcockpit;

CREATE TABLE IF NOT EXISTS recent_lp (
    id INT,
    status VARCHAR(255) NOT NULL,
    tag VARCHAR(255) NOT NULL,
    link VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    CONSTRAINT id_tag PRIMARY KEY (id, tag)
);

TRUNCATE TABLE recent_lp;

LOAD DATA LOCAL INFILE '/tmp/recent_lp.csv' \n
INTO TABLE recent_lp \n
FIELDS TERMINATED BY ',' \n
LINES TERMINATED BY '\n';
