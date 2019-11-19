from agent import PromoterAgent

def parse_args():
    # We can pass directly the .ini file from the promoter
    # To get these infos
    distro = config['distro']
    release = config['release']
    api_url = config['api_url']

    # These must be provided
    promote_name = config['promote_name']
    rollback_hash # need to check validity, we can't roll back, to a hash if it's too old.


    # Optional, but useful
    failed_hash
    # Print warning
    # Without a failed hash, the only way to roll back is to
    # repromote everything to the rollback_hash
    return {}

if __name__ == "__main__":
    # rollback running as standalone tool
    config = parse_args()
    # Print Warning
    warning = ("This tool is about to roll back promotion to a know"
               "good state. If you are calling this tool by hand, you should ensure that no other"
               "promotion process is disbled, as this tool doesn't syncronize with any active promotion process"
               "and can't lock the resources it's about to modify. Please type 'yes' if you want to continue")
    if not args.skip_warning:
        print(warning)
    agent = PromoterAgent(config=config)
    transaction = agent.start_transaction()
    transaction.rollback(config['hash'])
