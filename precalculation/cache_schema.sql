-- SQLite3 schema for precalculating stuff for big-fam's tables

-- bgc_domains (only best hits in the case of sub_pfam)
CREATE TABLE IF NOT EXISTS bgc_domains (
    bgc_id INTEGER NOT NULL,
    hmm_id INTEGER NOT NULL,
    UNIQUE(bgc_id, hmm_id)
);
CREATE INDEX IF NOT EXISTS bgc_domains_bgc ON bgc_domains(bgc_id);
CREATE INDEX IF NOT EXISTS bgc_domains_hmm ON bgc_domains(hmm_id);

-- bgc_summary
CREATE TABLE IF NOT EXISTS bgc_summary (
    bgc_id INTEGER NOT NULL,
    cds_count INTEGER NOT NULL,
    UNIQUE(bgc_id)
);
CREATE INDEX IF NOT EXISTS bgc_summary_id ON bgc_summary(bgc_id);
CREATE INDEX IF NOT EXISTS bgc_summary_cds ON bgc_summary(cds_count);

-- gcf_summary
CREATE TABLE IF NOT EXISTS gcf_summary (
    gcf_id INTEGER NOT NULL,
    core_members INTEGER NOT NULL,
    putative_members INTEGER NOT NULL,
    UNIQUE(gcf_id)
);
CREATE INDEX IF NOT EXISTS gcf_summary_id ON gcf_summary(gcf_id);
CREATE INDEX IF NOT EXISTS gcf_summary_core ON gcf_summary(core_members);
CREATE INDEX IF NOT EXISTS gcf_summary_putative ON gcf_summary(putative_members);

-- gcf_summary_dataset
CREATE TABLE IF NOT EXISTS gcf_summary_dataset (
    gcf_id INTEGER NOT NULL,
    dataset_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    UNIQUE(gcf_id, dataset_id)
);
CREATE INDEX IF NOT EXISTS gcf_summary_dataset_gcfid ON gcf_summary_dataset(gcf_id, dataset_id, count);
CREATE INDEX IF NOT EXISTS gcf_summary_dataset_dsid ON gcf_summary_dataset(dataset_id, gcf_id, count);

-- gcf_summary_taxon
CREATE TABLE IF NOT EXISTS gcf_summary_taxon (
    gcf_id INTEGER NOT NULL,
    taxon_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    UNIQUE(gcf_id, taxon_id)
);
CREATE INDEX IF NOT EXISTS gcf_summary_taxon_gcfid ON gcf_summary_taxon(gcf_id, taxon_id, count);
CREATE INDEX IF NOT EXISTS gcf_summary_taxon_taxid ON gcf_summary_taxon(taxon_id, gcf_id, count);

-- gcf_summary_class
CREATE TABLE IF NOT EXISTS gcf_summary_class (
    gcf_id INTEGER NOT NULL,
    chem_subclass_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    UNIQUE(gcf_id, chem_subclass_id)
);
CREATE INDEX IF NOT EXISTS gcf_summary_class_gcfid ON gcf_summary_class(gcf_id, chem_subclass_id, count);
CREATE INDEX IF NOT EXISTS gcf_summary_class_classid ON gcf_summary_class(chem_subclass_id, gcf_id, count);

-- gcf_summary_domains
CREATE TABLE IF NOT EXISTS gcf_domains (
    gcf_id INTEGER NOT NULL,
    hmm_id INTEGER NOT NULL,
    UNIQUE(gcf_id, hmm_id)
);
CREATE INDEX IF NOT EXISTS gcf_domains_gcfid ON gcf_domains(gcf_id);
CREATE INDEX IF NOT EXISTS gcf_domains_hmmid ON gcf_domains(hmm_id);