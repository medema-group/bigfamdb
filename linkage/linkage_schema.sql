-- SQLite3 schema for linkage matadata to mibig, antismashdb and ncbi

CREATE TABLE IF NOT EXISTS linkage_ncbi (
	bgc_id INTEGER NOT NULL,
	nuccore_acc VARCHAR(50) NOT NULL,
	start_loc INTEGER NOT NULL,
	end_loc INTEGER NOT NULL,
	UNIQUE(bgc_id)
);

CREATE TABLE IF NOT EXISTS linkage_antismashdb (
	bgc_id INTEGER NOT NULL,
	nuccore_acc VARCHAR(50) NOT NULL,
	start_loc INTEGER NOT NULL,
	end_loc INTEGER NOT NULL,
	UNIQUE(bgc_id)
);

CREATE TABLE IF NOT EXISTS linkage_mibig (
	bgc_id INTEGER NOT NULL,
	mibig_acc VARCHAR(16) NOT NULL,
	UNIQUE(bgc_id)
);

CREATE TABLE IF NOT EXISTS linkage_study (
	dataset_id INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	doi VARCHAR(100) NOT NULL,
	UNIQUE(dataset_id)
);