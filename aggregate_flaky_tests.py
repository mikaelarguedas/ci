import argparse
from collections import OrderedDict
import sys

from jenkinsapi.custom_exceptions import UnknownJob
from jenkinsapi.jenkins import Jenkins

J = Jenkins('http://ci.ros2.org')


def get_aggregated_test_failures_across_builds(
        *, job=None, last_n_builds=10,
        include_skipped_tests=False, skip_missing_results=True):
    last_build_number = job.get_last_buildnumber()
    if last_build_number < last_n_builds:
        last_n_builds = last_build_number
        print(
            'will process only the last %d builds for job %s' % (last_n_builds, job),
            file=sys.stderr)
    test_failures_list = list()
    for build_number in range(last_build_number, last_build_number - last_n_builds, -1):
        print('processing build %d' % build_number)
        test_failures_list += get_job_test_failures(
            job=job, build_number=build_number,
            include_skipped_tests=include_skipped_tests,
            skip_missing_results=skip_missing_results)
    return test_failures_list


def is_test_failure(test_result=None):
    if test_result is None:
        print('test_result is None, skipping', file=sys.stderr)
        return False
    return test_result[1].age > 0


def is_test_skipped(test_result=None):
    if test_result is None:
        print('test_result is None, skipping', file=sys.stderr)
        return False
    return test_result[1].status == 'SKIPPED'


def get_job_test_failures(
        *, job=None, build_number=None,
        include_skipped_tests=False, skip_missing_results=True):
    if job is None:
        print('job is None, skipping', file=sys.stderr)
        return list()
    if build_number is None:
        print('As build number should be provided, skipping %s' % job, file=sys.stderr)
        return list()
    build = job.get_build(build_number)
    if not build.has_resultset():
        return list()
    test_results = build.get_resultset()
    test_failures = list()
    for test_result in test_results.items():
        if not include_skipped_tests and is_test_skipped(test_result):
            continue
        if skip_missing_results and test_result[0].endswith('missing_result'):
            continue
        if is_test_failure(test_result) and test_result[0] not in test_failures:
            test_failures.append(test_result[0])

    return test_failures


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description='listing all tests failing at least once on a set of jobs.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--job-names',
        nargs='*',
        # default = ['nightly_osx_repeated'],
        default=[x for x in J.get_jobs_list() if x.rfind('_rep') != -1],
        help='List of jobs to find failing tests on')
    parser.add_argument(
        '-n',
        nargs='?',
        default=25,
        type=int,
        help='number of jobs to check')
    parser.add_argument(
        '--skip-missing-results',
        action='store_true',
        default=False
        )
    parser.add_argument(
        '--include-skipped-tests',
        action='store_true',
        default=False
        )

    args = parser.parse_args(argv)
    failing_tests = dict()
    for job in args.job_names:
        try:
            jobObject = J.get_job(job)
            print(job)
        except UnknownJob:
            continue
        test_failures_list = get_aggregated_test_failures_across_builds(
            job=jobObject, last_n_builds=args.n,
            include_skipped_tests=args.include_skipped_tests,
            skip_missing_results=args.skip_missing_results)
        agg_test_failures_list = list(set(test_failures_list))
        for test_failure in agg_test_failures_list:
            if test_failure in failing_tests.keys() and job not in failing_tests[test_failure]:
                failing_tests[test_failure].append(job)
            else:
                failing_tests[test_failure] = [job]
    ordered_failing_tests_dict = OrderedDict(sorted(failing_tests.items(), key=lambda t: t[0]))
    for key, value in ordered_failing_tests_dict.items():
        print(' - [ ] %s, %s' % (key, value))
    print(len(failing_tests.keys()))


if __name__ == '__main__':
    sys.exit(main())
