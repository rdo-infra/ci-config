import logging
import pprint
from common import DlrnClientError

class RollbackNotNeeded(Exception):
    pass

class RollbackError(Exception):
    pass

class PromoterTransaction(object):

    log = logging.getLogger('promoter')

    def __init__(self, promoter_agent):
        self.promoter_agent = promoter_agent
        self.checkpoints = None
        self.completed_steps = []
        self.incomplete_steps = ["containers", "qcows", "dlrn"]

    def start(self, attempt_hash, current_hash, name):
        ''' This method marks the checkpoint for a transaction
            having a checkpoint is optional, but would greatly
            help in rolling back.
        '''
        self.attempted_hash = attempt_hash
        self.rollback_hash_name = name
        self.rollback_hash = current_hash
        self.checkpoints = {
            "containers": "pending",
            "qcow": "pending",
            "dlrn": "pending",
        }
        self.completed_steps = []
        self.incomplete_steps = ["containers", "qcows", "dlrn"]

    def end(self):
        self.checkpoints = None
        self.rollback_hash = None
        self.rollback_hash_name = None
        self.attempted_hash = None
        self.completed_steps = []
        self.incomplete_steps = ["containers", "qcows", "dlrn"]


    def checkpoint(self, mark, progress):
        ''' Promoter can use this method to mark the state of
            advancement of a promotion critical section
        '''
        if progress == "start":
            self.checkpoints[mark] = "started"
        else:
            self.checkpoints[mark] = "completed"
            self.completed_steps.append(mark)
            self.incomplete_steps.remove(mark)



    def rollback(self, attempted_hash=None, rollback_hash=None, name=None, retry_promotion=False):
        ''' On success, the valid state hash is returned, it could be the attempted hash or the rollback hash
            On failure a RollbackError is raised
        '''

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


        # Check if the attempted hash was promoted and we don't really need to roll back
        if attempted_hash is not None:
            # For optimization, we don't check what was marked as completed in
            # checkpoints
            results = self.promoter_agent.validate_hash(attempted_hash, steps=self.incomplete_steps,
                                                        name=self.rollback_hash_name)
            if results['promotion_valid']:
                self.log.info("Attempted hash is fully promoted, not rolling back")
                raise RollbackNotNeeded("Attempted hash is fully promoted, not rolling back")

            # Check if we are really just missing the dlrn link
            if self.incomplete_steps == ['dlrn'] and results['dlrn']['hash_valid']:
                self.log.info("Attemptd hash {} is really just missing dlrn promotion", attempted_hash)
                # If we are allowed, retry the promotion once
                if retry_promotion:
                    try:
                        self.promoter_agent.dlrn_client.promote_hash(attempted_hash, name)
                        return attempted_hash
                    except DlrnClientError:
                        self.log.error("Promotion retry failed for hash %s."
                                       " Rolling back", attempted_hash)


        # Check if we can roll back to this hash.
        results = self.promoter_agent.validate_hash(rollback_hash)
        pprint.pprint(results)
        if results['hash_valid'] is False:
            self.log.error("Can't roll back to the specified hash: missing pieces")
            raise RollbackError("Rollback hash is not in a valid state")

        self.agent.promote(promote_items)

