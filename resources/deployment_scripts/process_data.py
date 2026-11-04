# Databricks notebook source
# MAGIC %md
# MAGIC # Data Processing Pipeline
# MAGIC
# MAGIC Download up to 70 arXiv PDFs, store metadata, and create chunks using
# MAGIC the shared DataProcessor. Lakebase synchronization is a separate job task.

# COMMAND ----------

from loguru import logger
from pyspark.sql import SparkSession

from arxiv_curator.config import get_env, load_config
from arxiv_curator.data_processor import DataProcessor

# COMMAND ----------

spark = SparkSession.builder.getOrCreate()
env = get_env(spark)
cfg = load_config("../../project_config.yml", env=env)

logger.info(f"Environment: {env}; catalog: {cfg.catalog}; schema: {cfg.schema}")

# COMMAND ----------

# Unity Catalog volumes must be created through SQL before making directories.
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {cfg.catalog}.{cfg.schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {cfg.catalog}.{cfg.schema}.{cfg.volume}")

processor = DataProcessor(spark=spark, config=cfg)
processor.process_and_save()
