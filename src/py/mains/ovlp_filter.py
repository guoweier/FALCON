from falcon_kit.multiproc import Pool
import argparse
import subprocess as sp
import shlex
import argparse
import sys

LOG = sys.stderr.write

def write_nothing(*args):
    """
    To use,
      LOG = noop
    """

def syscall(cmd):
    """Return stdout.
    Raise if empty.
    Raise on non-zero exit-code.
    """
    LOG('$ %s\n' %cmd)
    output = sp.check_output(shlex.split(cmd))
    if not output:
        msg = '%r failed to produce any output.' %cmd
        LOG('WARNING: %s\n' %msg)
    return output

def filter_stage1(input_):
    db_fn, fn, max_diff, max_ovlp, min_ovlp, min_len = input_
    try:
        ignore_rtn = []
        current_q_id = None
        contained = False
        ave_idt = 0.0
        all_over_len = 0.0
        overlap_data = {"5p":0, "3p":0}
        q_id = None
        cmd = "LA4Falcon -mo %s %s" % (db_fn, fn)
        for l in syscall(cmd).splitlines():
            l = l.strip().split()
            q_id, t_id = l[:2]

            if q_id != None and q_id != current_q_id:

                left_count = overlap_data["5p"]
                right_count = overlap_data["3p"]
            
                if abs(left_count - right_count) > max_diff:
                    ignore_rtn.append( current_q_id )
                elif left_count > max_ovlp or right_count > max_ovlp:
                    ignore_rtn.append( current_q_id )
                elif left_count < min_ovlp or right_count < min_ovlp: 
                    ignore_rtn.append( current_q_id )

                overlap_data = {"5p":0, "3p":0}
                current_q_id = q_id
                contained = False
                ave_idt = 0.0
                all_over_len = 0.0

            overlap_len = -int(l[2])
            idt = float(l[3])
            q_s, q_e, q_l = int(l[5]), int(l[6]), int(l[7])
            t_s, t_e, t_l = int(l[9]), int(l[10]), int(l[11])

            if idt < 90:
                continue

            if q_l < min_len or t_l < min_len:
                continue

            if not contained:
                if l[-1] in ("contains", "overlap"):
                    ave_idt += idt * overlap_len
                    all_over_len += overlap_len
                if q_s == 0:
                    overlap_data["5p"] += 1
                elif q_e == q_l:
                    overlap_data["3p"] += 1

        if q_id !=  None:
            left_count = overlap_data["5p"]
            right_count = overlap_data["3p"]
            if abs(left_count - right_count) > max_diff:
                ignore_rtn.append( current_q_id )
            elif left_count > max_ovlp or right_count > max_ovlp:
                ignore_rtn.append( current_q_id )
            elif left_count < min_ovlp or right_count < min_ovlp: 
                ignore_rtn.append( current_q_id )
            
        return fn, ignore_rtn

    except (KeyboardInterrupt, SystemExit):
        return

def filter_stage2(input_):
    db_fn, fn, max_diff, max_ovlp, min_ovlp, min_len, ignore_set = input_
    try:
        contained_id = set()
        cmd = "LA4Falcon -mo %s %s" % (db_fn, fn)
        for l in syscall(cmd).splitlines():
            l = l.strip().split()
            q_id, t_id = l[:2]

            q_s, q_e, q_l = int(l[5]), int(l[6]), int(l[7])
            t_s, t_e, t_l = int(l[9]), int(l[10]), int(l[11])

            idt = float(l[3])
            if idt < 90:
                continue

            if q_l < min_len or t_l < min_len:
                continue

            if q_id in ignore_set:
                continue
            if t_id in ignore_set:
                continue
            if l[-1] == "contained":
                contained_id.add(q_id)
            if l[-1] == "contains":
                contained_id.add(t_id)
        return fn, contained_id 

    except (KeyboardInterrupt, SystemExit):
        return

def filter_stage3(input_):
    db_fn, fn, max_diff, max_ovlp, min_ovlp, min_len, ignore_set, contained_set, bestn = input_
    try:
        ovlp_output = []
        current_q_id = None
        cmd = "LA4Falcon -mo %s %s" % (db_fn, fn)
        for l in syscall(cmd).splitlines():
            l = l.strip().split()
            q_id, t_id = l[:2]


            if current_q_id == None:
                current_q_id = q_id
                overlap_data = {"5p":[], "3p":[]}

            elif q_id != current_q_id:

                left = overlap_data["5p"]
                right = overlap_data["3p"]
                left.sort()
                right.sort()

                for i in xrange(len(left)):
                    score, m_range, ovlp = left[i]
                    ovlp_output.append(ovlp)
                    #print " ".join(ovlp), read_end_data[current_q_id] 
                    if i >= bestn and m_range > 1000:
                        break
                
                for i in xrange(len(right)):
                    score, m_range, ovlp = right[i]
                    ovlp_output.append(ovlp)
                    #print " ".join(ovlp), read_end_data[current_q_id]
                    if i >= bestn and m_range > 1000:
                        break

                overlap_data = {"5p":[], "3p":[]}
                current_q_id = q_id

            if q_id in contained_set:
                continue
            if t_id in contained_set:
                continue
            if q_id in ignore_set:
                continue
            if t_id in ignore_set:
                continue

            overlap_len = -int(l[2])
            idt = float(l[3])
            q_s, q_e, q_l = int(l[5]), int(l[6]), int(l[7])
            t_s, t_e, t_l = int(l[9]), int(l[10]), int(l[11])

            if idt < 90:
                continue
            if q_l < min_len or t_l < min_len:
                continue

            if q_s == 0:
                overlap_data["5p"].append( (-overlap_len,  t_l - (t_e - t_s),  l) )
            elif q_e == q_l:
                overlap_data["3p"].append( (-overlap_len, t_l - (t_e - t_s), l) )

        left = overlap_data["5p"]
        right = overlap_data["3p"]
        left.sort()
        right.sort()


        for i in xrange(len(left)):
            score, m_range, ovlp = left[i]
            ovlp_output.append(ovlp)
            #print " ".join(ovlp), read_end_data[current_q_id] 
            if i >= bestn and m_range > 1000:
                break

        for i in xrange(len(right)):
            score, m_range, ovlp = right[i]
            ovlp_output.append(ovlp)
            #print " ".join(ovlp), read_end_data[current_q_id]
            if i >= bestn and m_range > 1000:
                break

        return fn, ovlp_output
    except (KeyboardInterrupt, SystemExit):
        return

def parse_args(argv):
    parser = argparse.ArgumentParser(description='a simple multi-processes LAS ovelap data filter')
    parser.add_argument('--n_core', type=int, default=4,
                        help='number of processes used for generating consensus; '
                        '0 for main process only (default=%(default)s)')
    parser.add_argument('--fofn', type=str, help='file contains the path of all LAS file to be processed in parallel')
    parser.add_argument('--db', type=str, dest='db_fn', help='read db file path')
    parser.add_argument('--max_diff', type=int, help="max difference of 5' and 3' coverage")
    parser.add_argument('--max_cov', type=int, help="max coverage of 5' or 3' coverage")
    parser.add_argument('--min_cov', type=int, help="min coverage of 5' or 3' coverage")
    parser.add_argument('--min_len', type=int, default=2500, help="min length of the reads (default=%(default)s)")
    parser.add_argument('--bestn', type=int, default=10, help="output at least best n overlaps on 5' or 3' ends if possible (default=%(default)s)")
    parser.add_argument('--debug', '-g', action='store_true', help="single-threaded, plus other aids to debugging")
    parser.add_argument('--silent', action='store_true', help="suppress cmd reporting on stderr")
    args = parser.parse_args(argv[1:])
    return args

def fc_ovlp_filter(n_core, fofn, max_diff, max_cov, min_cov, min_len, bestn, db_fn, debug, silent):
    global LOG
    if silent:
        LOG = write_nothing
    exe_pool = Pool(n_core)

    file_list = open(fofn).read().split("\n")
    inputs = []
    for fn in file_list:
        if len(fn) != 0:
            inputs.append( (db_fn, fn, max_diff, max_cov, min_cov, min_len) )
    
    ignore_all = []
    for res in exe_pool.imap(filter_stage1, inputs):  
        ignore_all.extend( res[1] )

    inputs = []
    ignore_all = set(ignore_all)
    for fn in file_list:
        if len(fn) != 0:
            inputs.append( (db_fn, fn, max_diff, max_cov, min_cov, min_len, ignore_all) )
    contained = set()
    for res in exe_pool.imap(filter_stage2, inputs):  
        contained.update(res[1])
        #print res[0], len(res[1]), len(contained)

    #print "all", len(contained)
    inputs = []
    ignore_all = set(ignore_all)
    for fn in file_list:
        if len(fn) != 0:
            inputs.append( (db_fn, fn, max_diff, max_cov, min_cov, min_len, ignore_all, contained, bestn) )
    for res in exe_pool.imap(filter_stage3, inputs):  
        for l in res[1]:
            print " ".join(l)

def main(*argv):
    args = parse_args(argv)
    fc_ovlp_filter(**vars(args))