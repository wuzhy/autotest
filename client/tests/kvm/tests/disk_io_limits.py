import logging, time, os, re, string
from autotest_lib.client.common_lib import error
from autotest_lib.client.bin import utils
from autotest_lib.client.virt import virt_utils


def run_disk_io_limits(test, params, env):
    """
    KVM guest stop test:
    1) Get a VM object
    2) Log into a guest
    3) Execute benchmarks of disk io limits
    4) Made a regexp search on dd output to isolate the throughput, convert
it to an float 
    5) Compare with the desired value, failing it if the criteria is not
met.
    6) Close the session

    @param test: kvm test object
    @param params: Dictionary with the test parameters
    @param env: Dictionary with test environment.
    """
    vm = env.get_vm(params["main_vm"])
    vm.verify_alive()
    session = vm.wait_for_login()

    # The default unit of io_limits is MB/s
    io_limits = params.get("io_limits", "100 MB/s")
    io_limits = re.findall(r'[0-9]* MB\/s', io_limits)
    if not io_limits:
        raise error.TestFail('Fail to get I/O rate limit.')

    io_limits = string.join(io_limits)
    io_limits = io_limits.replace(' MB/s','')
    io_limits = float(io_limits)

    try:
        output = session.cmd_output('dd if=/dev/vda of=/dev/null bs=256K count=128 iflag=direct')
        bps_bytes = re.findall(r'[0-9]* bytes', output)
        if not bps_bytes:
           raise error.TestFail('Fail to get I/O bytes at runtime.')

        bps_seconds = re.findall(r'[0-9]*[.][0-9]* s', output)
        if not bps_seconds:
           raise error.TestFail('Fail to get I/O seconds at runtime.')

        bps_bytes = string.join(bps_bytes)
        bps_bytes = bps_bytes.replace(' bytes','')
        bps_bytes = float(bps_bytes)

        bps_seconds = string.join(bps_seconds)
        bps_seconds = bps_seconds.replace(' s','')
        bps_seconds = float(bps_seconds)
        if bps_seconds == 0:
           raise error.TestFail('The I/O seconds at runtime is zero.')

        logging.debug("bps_bytes = %d, bps_seconds = %f", bps_bytes, bps_seconds)
        bps_iorate = (bps_bytes / (1024 * 1024)) / bps_seconds

        logging.debug("io_limits = %f, bps_iorate = %f", io_limits, bps_iorate)
        if bps_iorate > io_limits:
           raise error.TestFail('Throughput has exceeded threshold.')
        else:
           logging.info("The limit criteria is met...")
    finally:
        session.close()
