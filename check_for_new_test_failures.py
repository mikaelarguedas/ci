from collections import defaultdict

from jenkinsapi.jenkins import Jenkins
J = Jenkins('http://ci.ros2.org')

def get_nightly_test_failures(os, last_n_builds=25):
    jobname = 'nightly_win_rep' if os is 'windows' else 'nightly_%s_repeated' % os
    print('Getting test failures for the last %i builds of %s' % (last_n_builds, jobname))
    job = J.get_job(jobname)
    last_build_number = job.get_last_buildnumber()
    nightly_test_failures = set()
    test_failure_occurences = defaultdict(dict)
    last_n_builds = min(last_n_builds, last_build_number)
    for build_number in range(last_build_number-last_n_builds+1, last_build_number+1):
        this_nightly_test_failures = get_job_test_failures(job, build_number)
        print('%i test failures for build number %i' % (len(this_nightly_test_failures), build_number))
        for failure in this_nightly_test_failures:
            if failure not in test_failure_occurences:
                test_failure_occurences[failure] = []
            test_failure_occurences[failure].append(build_number)
        nightly_test_failures |= this_nightly_test_failures
    print('%i total test failures for job %s' % (len(nightly_test_failures), jobname))
    return nightly_test_failures, test_failure_occurences

def is_test_failure(test_result):
    return test_result[1].age > 0 and test_result[1].status != 'SKIPPED'

def get_job_test_failures(job, build_number = None):
    build = job.get_last_build() if build_number is None else job.get_build(build_number)
    if not build.has_resultset():
        return set()
    test_results = build.get_resultset()
    test_failures = set([test[0] for test in test_results.items() if is_test_failure(test)])
    return test_failures

# PARAMETERS
os = 'linux'

# For checking if test failures in a CI job are flaky or not:
jobname = 'ci_%s' % os
build_number = 629

# If you want to check for occurences of a specific test failure, use:
test_name = 'TestStateMachineInfo.available_transitions'


nightly_test_failures, test_failure_occurences = get_nightly_test_failures(os)
job = J.get_job(jobname)
test_failures = get_job_test_failures(job, build_number)
print("test_failures")
print('\n'.join(nightly_test_failures))
print('\n'.join(['%s: %s' % (failure, jobs) for failure, jobs in test_failure_occurences.items()]))
existing_test_failures = test_failures & nightly_test_failures
new_test_failures = test_failures - existing_test_failures

print('New test failures for build %i of job %s:' % (build_number, jobname))
print('\n'.join(new_test_failures))

print('new test failure' if test_name not in test_failure_occurences else 'existing: %s' % test_failure_occurences[test_name])

