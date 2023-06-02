import time
import sys
import json
import gzip
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.environ['TZ'] = 'UTC'

# I need to rework this to capture all possible time formats
def convert_epoch_to_human_readable(file_path, node_type):
    if node_type == "Observation":
        with gzip.open(file_path, "rt") as fp:
            observation_lines = fp.readlines()
            for line in observation_lines:
                line = json.loads(line)
                line_time = line["effectiveDateTime"].split("T")
                line_time = line_time[0]
                # print("THE VALUE OF LKNE TIME", line_time)
                epoch_time = int(
                    time.mktime(
                        time.strptime(
                            line_time,
                            "%Y-%m-%d")))
                # logger.info(epoch_time)
                line["effectiveDateTime"] = str(epoch_time)
                print(json.dumps(line))

    elif node_type == "Condition":
        with gzip.open(file_path, "rt") as fp:
            observation_lines = fp.readlines()
            for line in observation_lines:
                line = json.loads(line)
                line_time = line["onsetDateTime"].split("T")
                line_time = line_time[0]
                # print("THE VALUE OF LKNE TIME", line_time)
                epoch_time = int(
                    time.mktime(
                        time.strptime(
                            line_time,
                            "%Y-%m-%d")))
                # logger.info(epoch_time)
                line["onsetDateTime"] = str(epoch_time)

                if "abatementDateTime" in line:
                    line_time = line["abatementDateTime"].split("T")
                    line_time = line_time[0]
                    # print("THE VALUE OF LKNE TIME", line_time)
                    epoch_time = int(
                        time.mktime(
                            time.strptime(
                                line_time,
                                "%Y-%m-%d")))
                    # logger.info(epoch_time)
                    line["abatementDateTime"] = str(epoch_time)
                    print(json.dumps(line))

    elif node_type == "Specimen":
        with gzip.open(file_path, "rt") as fp:
            observation_lines = fp.readlines()
            for line in observation_lines:
                line = json.loads(line)
                line_time = line["collection"]["collectedDateTime"].split("T")
                line_Date = line_time[0]
                #(line_time[1] != "00:00:00+00:00")
                if line_time[1] != "00:00:00+00:00":
                    if line_time[1] == "00:00:00Z":
                        epoch_dateTime = int(
                        time.mktime(
                            time.strptime(
                                line_time[0],
                                "%Y-%m-%d")))
                        line["collection"]["collectedDateTime"] = str(
                            epoch_dateTime)
                    else:
                        line_time[1] = line_time[1].split("+")[0]
                        line_DateTime = line_time[0] + " " + line_time[1]
                        epoch_dateTime = int(
                            time.mktime(
                                time.strptime(
                                    line_DateTime,
                                    "%Y-%m-%d %H:%M:%S")))
                        line["collection"]["collectedDateTime"] = str(
                            epoch_dateTime)

                # print("THE VALUE OF LKNE TIME", line_time)
                epoch_date = int(
                    time.mktime(
                        time.strptime(
                            line_Date,
                            "%Y-%m-%d")))

                # logger.info(epoch_time)
                line["collection"]["collectedDate"] = str(epoch_date)
                # need to have something for date time

                print(json.dumps(line))


    elif node_type == "Measurement":
        with gzip.open(file_path, "rt") as fp:
            observation_lines = fp.readlines()
            for line in observation_lines:
                line = json.loads(line)
                line_time = line["effectiveDateTime"].split("T")
                line_Date = line_time[0]
                #print("THE VLAUE OF LINE TIME", line_time[1])
                if line_time[1] != "00:00:00+00:00":
                    if line_time[1] == "00:00:00Z":
                        epoch_dateTime = int(
                        time.mktime(
                            time.strptime(
                                line_time[0],
                                "%Y-%m-%d")))
                        line["collection"]["collectedDateTime"] = str(
                            epoch_dateTime)
                        
                    line_time[1] = line_time[1].split("+")[0]
                    line_DateTime = line_time[0] + " " + line_time[1]
                    epoch_dateTime = int(
                        time.mktime(
                            time.strptime(
                                line_DateTime,
                                "%Y-%m-%d %H:%M:%S")))
                    line["measurement_datetime"] = str(
                        epoch_dateTime)

                # print("THE VALUE OF LKNE TIME", line_time)
                epoch_date = int(
                    time.mktime(
                        time.strptime(
                            line_Date,
                            "%Y-%m-%d")))

                # logger.info(epoch_time)
                line["measurement_date"] = str(epoch_date)
                # need to have something for date time

                print(json.dumps(line))

    elif node_type == "Encounter":
        with gzip.open(file_path, "rt") as fp:
            observation_lines = fp.readlines()
            for line in observation_lines:
                line = json.loads(line)
                line_time = line["period"]["start"].split("T")
                line_Date = line_time[0]
                #print("THE VLAUE OF LINE TIME", line_time[1])
                if line_time[1] != "00:00:00+00:00":
                    if line_time[1] == "00:00:00Z":
                        epoch_dateTime = int(
                        time.mktime(
                            time.strptime(
                                line_time[0],
                                "%Y-%m-%d")))
                        line["visit_start_datetime"] = str(
                            epoch_dateTime)
                    else:
                        line_time[1] = line_time[1].split("+")[0]
                        line_DateTime = line_time[0] + " " + line_time[1]
                        epoch_dateTime = int(
                            time.mktime(
                                time.strptime(
                                    line_DateTime,
                                    "%Y-%m-%d %H:%M:%S")))
                        line["visit_start_datetime"] = str(
                            epoch_dateTime)

                # print("THE VALUE OF LKNE TIME", line_time)
                epoch_date = int(
                    time.mktime(
                        time.strptime(
                            line_Date,
                            "%Y-%m-%d")))

                # logger.info(epoch_time)
                line["visit_start_date"] = str(epoch_date)

                line_time = line["period"]["end"].split("T")
                line_Date = line_time[0]
                #print("THE VLAUE OF LINE TIME", line_time[1])
                if line_time[1] != "00:00:00+00:00":
                    if line_time[1] == "00:00:00Z":
                        epoch_dateTime = int(
                        time.mktime(
                            time.strptime(
                                line_time[0],
                                "%Y-%m-%d")))
                        line["visit_end_datetime"] = str(
                            epoch_dateTime)
                    else:
                        line_time[1] = line_time[1].split("+")[0]
                        line_DateTime = line_time[0] + " " + line_time[1]
                        epoch_dateTime = int(
                            time.mktime(
                                time.strptime(
                                    line_DateTime,
                                    "%Y-%m-%d %H:%M:%S")))
                        line["visit_end_datetime"] = str(
                            epoch_dateTime)

                # print("THE VALUE OF LKNE TIME", line_time)
                epoch_date = int(
                    time.mktime(
                        time.strptime(
                            line_Date,
                            "%Y-%m-%d")))

                # logger.info(epoch_time)
                line["visit_end_date"] = str(epoch_date)

                print(json.dumps(line))


convert_epoch_to_human_readable(sys.argv[1], sys.argv[2])
