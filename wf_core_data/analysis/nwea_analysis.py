import wf_core_data.utils
import pandas as pd
import numpy as np
import inflection
import collections
import itertools
import functools
import os
import logging

logger = logging.getLogger(__name__)

TIME_FRAME_ID_VARIABLES_NWEA = [
    'school_year',
    'term'
]

STUDENT_ID_VARIABLES_NWEA = [
    'legal_entity',
    'student_id_nwea'
]

STUDENT_INFO_VARIABLES_NWEA = [
    'first_name',
    'last_name'
]

STUDENT_ASSIGNMENT_VARIABLES_NWEA = [
    'school',
    'teacher_last_first',
    'classroom',
    'grade'
]

ASSESSMENT_ID_VARIABLES_NWEA = [
    'subject',
    'course'
]

RESULTS_VARIABLES_NWEA = [
    'test_date',
    'rit_score',
    'rit_score_sem',
    'percentile',
    'percentile_se'
]

TERMS_NWEA = (
    'Fall',
    'Winter',
    'Spring'
)

ASSESSMENTS_NWEA = collections.OrderedDict((
    ('Language Arts', [
        'Reading',
        'Reading (Spanish)',
        'Language Usage'
    ]),
    ('Mathematics', [
        'Math K-12'
    ])
))

SUBJECTS_NWEA = list(ASSESSMENTS_NWEA.keys())

COURSES_NWEA=list(itertools.chain(*ASSESSMENTS_NWEA.values()))

def fetch_results_local_directory_nwea(
    path,
    file_extensions=['.csv', '.CSV']
):
    if not os.path.exists(path):
        raise ValueError('Path \'{}\' not found'.format(path))
    if not os.path.isdir(path):
        raise ValueError('Object at \'{}\' is not a directory'.format(path))
    paths = list()
    for directory_entry in os.listdir(path):
        file_path = os.path.join(
            path,
            directory_entry
        )
        if not os.path.isfile(file_path):
            continue
        file_extension = os.path.splitext(os.path.normpath(file_path))[1]
        if file_extension not in file_extensions:
            continue
        paths.append(file_path)
    if len(paths) == 0:
        raise ValueError('No files of type {} found in directory'.format(file_extensions))
    results = fetch_results_local_files_nwea(paths)
    return results

def fetch_results_local_files_nwea(
    paths
):
    results_list = list()
    for path in paths:
        results_file = fetch_results_local_file_nwea(
            path=path
        )
        results_list.append(results_file)
    results = pd.concat(results_list)
    return results

def fetch_results_local_file_nwea(
    path
):
    if not os.path.exists(path):
        raise ValueError('File \'{}\' not found'.format(path))
    if not os.path.isfile(path):
        raise ValueError('Object at \'{}\' is not a file'.format(path))
    results = pd.read_csv(
        path,
        dtype='object'
    )
    return results

def parse_results_nwea(results):
    test_events = extract_test_events_nwea(results)
    student_info, student_info_changes = extract_student_info_nwea(results)
    student_assignments = extract_student_assignments_nwea(results)
    return test_events, student_info, student_info_changes, student_assignments

def extract_test_events_nwea(
    results
):
    test_events = (
        results
        .rename(columns={
            'TermTested': 'term_school_year',
            'DistrictName': 'legal_entity',
            'Subject': 'subject',
            'Course': 'course',
            'StudentID': 'student_id_nwea',
            'TestDate': 'test_date',
            'StartRIT': 'rit_score',
            'StartRITSEM': 'rit_score_sem',
            'StartPercentile': 'percentile',
            'StartPercentileSE': 'percentile_se'
        })
    )
    test_events['term'] = test_events['term_school_year'].apply(lambda x: x.split(' ')[0])
    test_events['school_year'] = test_events['term_school_year'].apply(lambda x: x.split(' ')[1])
    test_events['term'] = pd.Categorical(
        test_events['term'],
        categories=TERMS_NWEA,
        ordered=True
    )
    test_events['subject'] = pd.Categorical(
        test_events['subject'],
        categories=SUBJECTS_NWEA,
        ordered=True
    )
    test_events['course'] = pd.Categorical(
        test_events['course'],
        categories=COURSES_NWEA,
        ordered=True
    )
    test_events['test_date'] = test_events['test_date'].apply(wf_core_data.utils.to_date)
    test_events['rit_score'] = pd.to_numeric(test_events['rit_score']).astype('float')
    test_events['rit_score_sem'] = pd.to_numeric(test_events['rit_score_sem']).astype('float')
    test_events['percentile'] = pd.to_numeric(test_events['percentile']).astype('float')
    test_events['percentile_se'] = pd.to_numeric(test_events['percentile_se'].replace('<1', 0.5)).astype('float')
    test_events = test_events.reindex(columns=
        TIME_FRAME_ID_VARIABLES_NWEA +
        ASSESSMENT_ID_VARIABLES_NWEA +
        STUDENT_ID_VARIABLES_NWEA +
        RESULTS_VARIABLES_NWEA
    )
    test_events.set_index(
        (
            TIME_FRAME_ID_VARIABLES_NWEA +
            ASSESSMENT_ID_VARIABLES_NWEA +
            STUDENT_ID_VARIABLES_NWEA
        ),
        inplace=True
    )
    test_events.sort_index(inplace=True)
    return test_events

def extract_student_info_nwea(
    results
):
    student_info = (
        results
        .rename(columns= {
            'TermTested': 'term_school_year',
            'DistrictName': 'legal_entity',
            'StudentID': 'student_id_nwea',
            'StudentLastName': 'last_name',
            'StudentFirstName': 'first_name'
        })
    )
    student_info['term'] = student_info['term_school_year'].apply(lambda x: x.split(' ')[0])
    student_info['school_year'] = student_info['term_school_year'].apply(lambda x: x.split(' ')[1])
    student_info = (
        student_info
        .reindex(columns=
            STUDENT_ID_VARIABLES_NWEA +
            TIME_FRAME_ID_VARIABLES_NWEA +
            STUDENT_INFO_VARIABLES_NWEA
        )
        .drop_duplicates()
    )
    student_info_changes = (
        student_info
        .groupby(STUDENT_ID_VARIABLES_NWEA)
        .filter(lambda group: len(group.drop_duplicates(subset=STUDENT_INFO_VARIABLES_NWEA)) > 1)
    )
    student_info = (
        student_info
        .sort_values(TIME_FRAME_ID_VARIABLES_NWEA)
        .drop(columns=TIME_FRAME_ID_VARIABLES_NWEA)
        .groupby(STUDENT_INFO_VARIABLES_NWEA)
        .tail(1)
        .set_index(STUDENT_ID_VARIABLES_NWEA)
        .sort_index()
    )
    return student_info, student_info_changes

def extract_student_assignments_nwea(
    results
):
    student_assignments = (
        results
        .rename(columns= {
            'TermTested': 'term_school_year',
            'DistrictName': 'legal_entity',
            'StudentID': 'student_id_nwea',
            'SchoolName': 'school',
            'Teacher': 'teacher_last_first',
            'ClassName': 'classroom',
            'StudentGrade': 'grade'
        })
    )
    student_assignments['term'] = student_assignments['term_school_year'].apply(lambda x: x.split(' ')[0])
    student_assignments['school_year'] = student_assignments['term_school_year'].apply(lambda x: x.split(' ')[1])
    student_assignments = (
        student_assignments
        .reindex(columns=
            STUDENT_ID_VARIABLES_NWEA +
            TIME_FRAME_ID_VARIABLES_NWEA +
            STUDENT_ASSIGNMENT_VARIABLES_NWEA
        )
        .drop_duplicates()
        .set_index(
            STUDENT_ID_VARIABLES_NWEA +
            TIME_FRAME_ID_VARIABLES_NWEA
        )
        .sort_index()
    )
    return student_assignments

def summarize_by_student_nwea(
    test_events,
    student_info,
    min_growth_days=60,
    unstack_variables=['term'],
    filter_dict=None,
    select_dict=None
):
    new_index_variables = list(test_events.index.names)
    for unstack_variable in unstack_variables:
        new_index_variables.remove(unstack_variable)
    students = (
        test_events
        .unstack(unstack_variables)
    )
    students.columns = ['_'.join([inflection.underscore(variable_name) for variable_name in x]) for x in students.columns]
    underlying_data_columns = list(students.columns)
    rit_scores = (
        test_events
        .dropna(subset=['rit_score'])
        .sort_values('test_date')
        .groupby(new_index_variables)
        .agg(
            rit_score_starting_date=('test_date', lambda x: x.dropna().iloc[0]),
            rit_score_ending_date=('test_date', lambda x: x.dropna().iloc[-1]),
            starting_rit_score=('rit_score', lambda x: x.dropna().iloc[0]),
            ending_rit_score=('rit_score', lambda x: x.dropna().iloc[-1]),
        )
    )
    percentiles = (
        test_events
        .dropna(subset=['percentile'])
        .sort_values('test_date')
        .groupby(new_index_variables)
        .agg(
            percentile_starting_date=('test_date', lambda x: x.dropna().iloc[0]),
            percentile_ending_date=('test_date', lambda x: x.dropna().iloc[-1]),
            starting_percentile=('percentile', lambda x: x.dropna().iloc[0]),
            ending_percentile=('percentile', lambda x: x.dropna().iloc[-1]),
        )
    )
    students = (
        students
        .join(
            rit_scores,
            how='left'
        )
        .join(
            percentiles,
            how='left'
        )
    )
    students['rit_score_num_days'] = (
        np.subtract(
            students['rit_score_ending_date'],
            students['rit_score_starting_date']
        )
        .apply(lambda x: x.days)
    )
    students['rit_score_growth'] = np.subtract(
        students['ending_rit_score'],
        students['starting_rit_score']
    )
    students.loc[students['rit_score_num_days'] < min_growth_days, 'rit_score_growth'] = np.nan
    students['percentile_num_days'] = (
        np.subtract(
            students['percentile_ending_date'],
            students['percentile_starting_date']
        )
        .apply(lambda x: x.days)
    )
    students['percentile_growth'] = np.subtract(
        students['ending_percentile'],
        students['starting_percentile']
    )
    students.loc[students['percentile_num_days'] < min_growth_days, 'percentile_growth'] = np.nan
    students = students.join(
        student_info,
        how='left',
        on=['legal_entity', 'student_id_nwea']
    )
    students = students.reindex(columns=
        [
            'first_name',
            'last_name'
        ] +
        underlying_data_columns +
        [
            'rit_score_starting_date',
            'rit_score_ending_date',
            'rit_score_num_days',
            'starting_rit_score',
            'ending_rit_score',
            'rit_score_growth',
            'percentile_starting_date',
            'percentile_ending_date',
            'percentile_num_days',
            'starting_percentile',
            'ending_percentile',
            'percentile_growth'
        ]
    )
    if filter_dict is not None:
        students = wf_core_data.utils.filter_dataframe(
            dataframe=students,
            filter_dict=filter_dict
        )
    if select_dict is not None:
        students = wf_core_data.utils.select_from_dataframe(
            dataframe=students,
            select_dict=select_dict
        )
    return students

def summarize_by_group_nwea(
    students,
    grouping_variables=[
        'school_year',
        'legal_entity',
        'subject',
        'course'
    ],
    filter_dict=None,
    select_dict=None
):
    groups = (
        students
        .reset_index()
        .groupby(grouping_variables)
        .agg(
            num_valid_test_results=('student_id_nwea', 'count'),
            num_valid_rit_score_growth=('rit_score_growth', 'count'),
            mean_rit_score_growth=('rit_score_growth', 'mean'),
            num_valid_percentile=('ending_percentile', 'count'),
            mean_percentile=('ending_percentile', 'mean'),
            num_valid_percentile_growth=('percentile_growth', 'count'),
            mean_percentile_growth=('percentile_growth', 'mean')
        )
        .dropna(how='all')
    )
    groups = groups.loc[groups['num_valid_test_results'] > 0].copy()
    groups = groups.reindex(columns=[
        'num_valid_test_results',
        'num_valid_rit_score_growth',
        'mean_rit_score_growth',
        'num_valid_percentile',
        'mean_percentile',
        'num_valid_percentile_growth',
        'mean_percentile_growth'
    ])
    if filter_dict is not None:
        groups = wf_core_data.utils.filter_dataframe(
            dataframe=groups,
            filter_dict=filter_dict
        )
    if select_dict is not None:
        groups = wf_core_data.utils.select_from_dataframe(
            dataframe=groups,
            select_dict=select_dict
        )
    return groups