from pathlib import Path
from subprocess import CalledProcessError
from typing import Optional, IO, List, Tuple

import matplotlib.pyplot as plt
import networkx as nx
from pyspark import SparkContext
from pyspark.conf import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType


# if __all__ is not set then all attributes in the module can be accessed by import expect for those attributes that
# start with '_'. When __all__ is defined only those attributes are accessible.
# __all__ = ['get_slurm_id', 'get_slurm_dir']


def get_slurm_id() -> str:
    import subprocess
    slurm_id: Optional[IO[bytes]]

    try:
        slurm_id = subprocess.Popen("squeue -u $USER | tail -1 | awk {'print $1'}", shell=True,
                                    stdout=subprocess.PIPE).stdout
    except (OSError, ValueError, CalledProcessError, Exception):
        slurm_id = subprocess.Popen("ssh -f arc squeue -u $USER | tail -1 | awk {'print $1'}", shell=True,
                                    stdout=subprocess.PIPE).stdout
    return str(slurm_id.read().rstrip(), 'utf-8')


def get_slurm_dir() -> Path:
    return Path('/scratch', get_slurm_id())


# returns (SparkContext, SqlContext) objects.
def get_spark_sql_context(pyfiles: str) -> tuple[SparkContext, SparkSession]:
    import os

    config_lines: List[Tuple] = [tuple(a.rstrip().split(" ")) for a in
                                 open(os.environ['SPARK_CONFIG_FILE']).readlines()]
    conf = SparkConf()
    conf.setAll(config_lines)
    conf.setMaster("spark://%s:%s" % (os.environ['SPARK_MASTER_HOST'], os.environ['SPARK_MASTER_PORT']))
    conf.set("spark.speculation", "false")
    conf.set("spark.files", pyfiles)
    conf.set("spark.submit.pyFiles", pyfiles)
    print(f'configs:\n{conf.getAll()}')

    # sc.getConf() # get spark session and configuration
    sql_ctx = SparkSession.builder.config(conf=conf).getOrCreate()
    sc = sql_ctx.sparkContext
    print(f'spark ui: {sc.uiWebUrl}')
    # SQLContext(sc, sparkSession=sc.getConf())
    # sql_ctx=pyspark.sql.SparkSession.builder.getOrCreate()
    print((sc, sql_ctx))
    return sc, sql_ctx


def plot_graph(edge_list):
    gplot = nx.Graph()
    for row in edge_list.select('src', 'dst').take(1000):
        gplot.add_edge(row['src'], row['dst'])

    plt.subplot(121)
    nx.draw(gplot, with_labels=True, font_weight='bold')


'''
spark = SparkSession \
    .builder \
    .appName("PlotAPp") \
    .getOrCreate()

sqlContext = SQLContext(spark)

vertices = sqlContext.createDataFrame([
  ("a", "Alice", 34),
  ("b", "Bob", 36),
  ("c", "Charlie", 30),
  ("d", "David", 29),
  ("e", "Esther", 32),
("e1", "Esther2", 32),
  ("f", "Fanny", 36),
  ("g", "Gabby", 60),
    ("h", "Mark", 61),
    ("i", "Gunter", 62),
    ("j", "Marit", 63)], ["id", "name", "age"])

edges = sqlContext.createDataFrame([
  ("a", "b", "friend"),
  ("b", "a", "follow"),
  ("c", "a", "follow"),
  ("c", "f", "follow"),
  ("g", "h", "follow"),
  ("h", "i", "friend"),
  ("h", "j", "friend"),
  ("j", "h", "friend"),
    ("e", "e1", "friend")
], ["src", "dst", "relationship"])

g = GraphFrame(vertices, edges)
PlotGraph(g.edges)
'''


# Create custom function
def title_case(x: str) -> str:
    return x.strip().title()


def upper_case(x: str) -> str:
    return x.strip().upper()


upperCaseUDF = udf(lambda x: upper_case(x), StringType())
titleCaseUDF = udf(lambda x: title_case(x), StringType())
