"""Pushes the default First Day Information unit to a semester

The script will ensure the target course does not already have a First Day
Information unit before copying to it.

The template (copy-from) course Org Unit Id is 10646.

Provide the Otis Semester Code as command line argument 1.
"""

import argparse
import csv
import sys
import pandas as pd
import os 

import datahub
import dwnld

# sourceId = 10646  # OrgUnitId of the blank template course to copy from
# sourceOd = 16825
parser = argparse.ArgumentParser()
parser.add_argument('semester', help="Otis semester code (i.e. '202210')")
parser.add_argument('--dept', help='Department code')
parser.add_argument('--nocheck', action='store_true', help='Prevents input for user to confirm before copying')
parser.add_argument('--nopast', action='store_true', help='Suppresses check for past copies to a course before copying')
parser.add_argument('--sourceId', help="sourceId for template, (default 10646)")
args = parser.parse_args()

def runner(idlist, sourceId):
    """copies the First Day Information module to each course in idlist
    if it does not already exist
    """
    sourceId = 10646 if sourceId is None else sourceId
    copylist = []
    for id in idlist:
        data = dwnld.get_toc(id)
        first_day = []
        for module in data['Modules']:
            if 'First Day Information' in module['Title']:
                first_day.append(module)
        if not first_day:
            copylist.append(id)
    if copylist:
        print("There are {} courses without a First Day Information Unit".format(len(copylist)))
        copy = 'y' if args.nocheck else input("Would you like to copy? (Y/N): ")
        if copy.lower() in ("y", "yes"):
            for id in copylist:
                dwnld.course_copy(id, sourceId, ['Content', 'CourseFiles'])
        else:
            print("copy aborted")
    else:
        print("No courses to copy to")

def mklist(semester, dept, sourceId):
    """Returns a list of course offering ids that are children of the semester
    and do not have a First Day Information module
    """
    sourceId = 10646 if sourceId is None else sourceId
    
    semesterId = datahub.get_orgunit(semester)
    children = dwnld.get_children(semesterId, ouTypeId=3)
    childlist = [child['Identifier'] for child in children] # lists all org units from the children

    sem_report = os.path.join(datahub.REPORT_PATH, "Semester Course Reports", semester + "_SemesterReport.xlsx")
    df = pd.read_excel(sem_report)
    if dept:
        df = df[df['DeptCode'] == dept]
        childlist = [str(id) for id in df['OrgUnitId'] if str(id) in childlist] # lists all IDs from selected department that are in the child list

    contentobjects = datahub.CONTENT_OBJECTS

    with open(contentobjects, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        firstdaylist = []
        for row in reader:
            if 'First Day Information' in row['Title']:
                firstdaylist.append(row['OrgUnitId'])
    idlist = []
    for i in childlist:
        if i not in firstdaylist:
            if args.nopast == False:
                status = dwnld.get_copy_logs({"sourceOrgUnitId": sourceId,"destinationOrgUnitId": i})
                if status == 404: # make sure default was not deleted by instructor
                    idlist.append(i)
            else:
                idlist.append(i)
    return idlist

if __name__ == "__main__":
    idlist = mklist(args.semester, args.dept, args.sourceId)
    runner(idlist, args.sourceId)
