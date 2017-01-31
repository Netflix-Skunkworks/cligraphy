from nflx_oc.commands.dev.repos import run_for_all_repos


def configure(parser):
    parser.add_argument('pattern')


def main(args):
    run_for_all_repos("git grep '%s'" % args.pattern)
