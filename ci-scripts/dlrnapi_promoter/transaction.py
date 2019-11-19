import logging


class PromoterTransaction(object):

    log = logging.getLogger('promoter')

    def __init__(self, promoter_agent):
        self.promoter_agent = promoter_agent

        # marks = None means we never started a transaction
        self.rollback_items = None


    def start(self, attempt_hash, current_hash, name):
        ''' This method marks the checkpoint for a transaction
            having a checkpoint is optional, but would greatly
            help in rolling back.
        '''
        self.attempted_hash = attempt_hash
        self.rollback_hash_name = name
        self.rollback_hash = current_hash
        self.rollback_items = {
            "containers": None,
            "qcow": None
        }

    def end(self):
        self.rollback_items = None
        self.rollback_hash = None
        self.rollback_hash_name = None
        self.attempted_hash = None


    def checkpoint(self, mark, progress):
        ''' Promoter can use this method to mark the state of
            advancement of a promotion critical section
        '''
        if progress == "start":
            self.rollback_items[mark] = "check"
        else:
            self.rollback_items[mark] = "full"


    def rollback(self, attempted_hash=None, rollback_hash=None, name=None):

        # First thing we need a hash.
        # if we are in a transaction we can use the recorded hash
        # The attempted has is the one that supposedly failed

        if rollback_hash is None:
            try:
                rollback_hash = self.rollback_hash
            except AttributeError:
                self.log.error("This rollabck is not running during a transaction and no rollback hash was specified, please specify an hash to rollback to")
                raise

        if name is None:
            try:
                name = self.rollback_hash_name
            except AttributeError:
                self.log.error("This rollabck is not running during a transaction and no name was specified, please specify the promotion name to rollback")
                raise

        # if we have a specific hash taht filed, we can try to understand what succeded and rollback only taht
        if attempted_hash is None:
            try:
                # We have a specific hash tht failed
                attempted_hash =  self.attempted_hash
            except AttributeError:
                self.log.warning("Not in a transaction and no failed hash specified: the rollback function will nto n able to optimize the rollbackl and will have to redo the complete promotion")


        # Check if we can roll back to this hash.
        results = self.promoter_agent.validate_promotion(rollback_hash)
        if results['promotion_valid'] is False:
           self.log("Can't roll back to the specified hash: missing pieces")

        promote_items = {
            "qcow": "all",
            "containers": "all",
        }


        if self.rollback_items is not None:
            _, items = validate_hash(attempted_hash, items=rollback_items)
            # if validation  report promotion succeded, don't do anything.
            if results['hash']['name_points_hash'] == True:
                # Name already points to hash
                self.log.info("Attempted hash is fully promoted, not rolling back")
                return
            promote_items = complete_items

        self.agent.promote(proote_items)

