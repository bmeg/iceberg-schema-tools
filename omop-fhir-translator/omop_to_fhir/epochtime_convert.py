import datetime
import json
import sys
import logging
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.environ['TZ'] = 'UTC'


def date_validator(date):
    try:
        if (time.strptime(str(date), '%Y-%m-%d %H:%M:%S')):
            return True
    except ValueError:
        return False


def is_date(date):
    try:
        if (time.strptime(str(date), '%Y-%m-%d')):
            return True
    except ValueError:
        return False


def convert_time(file_path, node_type):
    date_key_list = []
    with open(file_path, "rt") as fp:
        observation_lines = fp.readlines()
        for line in observation_lines:
            line = json.loads(line)

            if (node_type == "Observation"):
                date_key_list = ["OBSERVATION_DATE", "OBSERVATION_DATETIME"]
            elif (node_type == "Condition"):
                date_key_list = [
                    "condition_start_date",
                    "condition_start_datetime",
                    "condition_end_date",
                    "condition_end_datetime"]
            elif (node_type == "Specimen"):
                date_key_list = ["specimen_date", "specimen_datetime"]
            elif (node_type == "Measurement"):
                date_key_list = ["measurement_date", "measurement_datetime"]
            elif (node_type == "Visit_Occurence"):
                date_key_list = ["VISIT_START_DATE",
                                 "VISIT_START_DATETIME",
                                 "VIST_END_DATE",
                                 "VISIT_END_DATETIME"]
            elif (node_type == "ProcedureOccurrence"):
                date_key_list = ["procedure_date",
                                 "procedure_datetime"]
            elif (node_type == "Drug_Exposure"):
                date_key_list = ["drug_exposure_start_date",
                                 "drug_exposure_start_datetime",
                                 "drug_exposure_end_date",
                                 "drug_exposure_end_datetime"]
            elif (node_type == "Device_Exposure"):
                date_key_list = ["device_exposure_start_date",
                                 "device_exposure_start_datetime",
                                 "device_exposure_end_date",
                                 "device_exposure_end_datetime"]

            for date_convertible in date_key_list:
                if date_convertible in line and str(
                        line[date_convertible]).isdigit():
                    new_time = datetime.datetime.fromtimestamp(
                        int(line[date_convertible]) / 1000).strftime(
                        '%Y-%m-%dT00:00:00+00:00')
                    line[date_convertible] = str(new_time)

                elif (date_convertible in line and date_validator(
                      str(line[date_convertible]))):

                    sep = line[date_convertible].split(" ")
                    line[date_convertible] = str(
                        sep[0]) + "T" + str(sep[1]) + "+00:00"

                elif (date_convertible in line and is_date(str(line[date_convertible]))):
                    line[date_convertible] = line[date_convertible] + \
                        "T00:00:00+00:00"

            if line:
                print(json.dumps(line))


convert_time(sys.argv[1], sys.argv[2])
