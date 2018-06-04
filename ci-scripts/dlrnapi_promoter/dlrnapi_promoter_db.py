import os
import sys

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

# there are no documented lengths for these in dlrnapi_client
MAX_LEN_COMMIT_HASH = 40
MAX_LEN_DISTRO_HASH = 40
MAX_LEN_REPO_HASH = 49
MAX_LEN_JOB_ID = 128
MAX_LEN_NOTES  = 256
MAX_LEN_URL = 256
MAX_LEN_PROMOTION_LINK = 32
MAX_LEN_JOBLIST = 512
MAX_LEN_USER = 16
MAX_LEN_RELEASE = 16

Base = declarative_base()
"""http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/api.html#declarative-api"""


class Repo(Base):
    """Dlrn repository ids (repository hashes) 

    These are first discovered by the promoter via periodic polling --> dlrnapi 
    for "the latest N promoted hashes, by symlink.
        
    They are returned from dlrnapi thus:

        {
            "timestamp": 1527536780,
            "distro_hash": "99947e05167cef613af384dd667869352d490145",
            "promote_name": "current-tripleo",
            "user": "ciuser",
            "repo_url": "https://trunk.rdoproject.org/centos7/8a/d7/8ad7ce315bf4e6cfce4494e7d022b2d0da39dad9_99947e05",
            "repo_hash": "8ad7ce315bf4e6cfce4494e7d022b2d0da39dad9_99947e05",
            "commit_hash": "8ad7ce315bf4e6cfce4494e7d022b2d0da39dad9"
        }
        
        Once they are known to the promoter, additional cireports can be
        fetched with the previous report time.  In this manner the 
        promoter need not duplicate polling for ci reports already fetched.
    """

    __tablename__ = 'repos'

    id = Column(Integer, nullable=False, unique=True, primary_key=True)

    jobresults = relationship("JobResult", back_populates="repos")

    commit_hash = Column(String(MAX_LEN_COMMIT_HASH), nullable=False)
    distro_hash = Column(String(MAX_LEN_DISTRO_HASH), nullable=False)
    repo_hash   = Column(String(MAX_LEN_REPO_HASH), nullable=False)
    repo_url    = Column(String(MAX_LEN_URL), nullable=False)
    release     = Column(String(MAX_LEN_RELEASE), nullable=False)

    last_ciresult_fetch = Column(DateTime, nullable=True)

    def __init__(self, commit_hash, distro_hash, repo_hash, repo_url, release):
        """A minor note on why all of these are explicity passed to ctor
        
        While much of this could be computed (e.g. repo_hash, url, etc), 
        it's explicity returned from the dlrnapi, and the rules for how these
        work are specifically the domain of the dlrnapi.  Were the business 
        logic/rules replicated here (e.g. compute the URL's or repo_hash directly)
        this would merely inject potential fault points
        """

        self.commit_hash = commit_hash
        self.distro_hash = distro_hash
        self.repo_hash = repo_hash
        self.repo_url = repo_url
        self.release = release
    
    def __repr__(self):
        return "<Repos (%s, %s)" % (self.release, self.release)


class JobResult(Base):
    """The dlrnapi returns an array of CI job results for each tested repo

        {
            "commit_hash": "85de06e2c40bfdc8dee80506f8d1d809a93b900e", 
            "distro_hash": "25e5ea4bc8f1b93ddd18c8dd2e0464a81f40402d", 
            "in_progress": false, 
            "job_id": "periodic-queens-rdo_trunk-featureset020-1ctlr_1comp_64gb", 
            "notes": "buildinfo,phase=rdophase2 id=https://trunk.rdoproject.org/centos7-queens/85/de/85de06e2c40bfdc8dee80506f8d1d809a93b900e_25e5ea4b,major=queens,minor=rdo_trunk 1527191768", 
            "success": true, 
            "timestamp": 1527191768, 
            "url": "https://thirdparty.logs.rdoproject.org/jenkins-periodic-queens-rdo_trunk-featureset020-1ctlr_1comp_64gb-60/console.txt.gz"
        }
    """

    __tablename__ = 'jobresults'
    
    id = Column(Integer, nullable=False, unique=True, primary_key=True)

    repo_id = Column(Integer, ForeignKey('repos.id'))
    repo = relationship("Repos", back_populates="jobresults")

    commit_hash = Column(String(MAX_LEN_COMMIT_HASH), nullable=False)
    distro_hash = Column(String(MAX_LEN_DISTRO_HASH), nullable=False)
    job_id      = Column(String(MAX_LEN_JOB_ID), nullable=False)
    notes       = Column(String(MAX_LEN_NOTES), nullable=False)
    url         = Column(String(MAX_LEN_URL), nullable=False)
    in_progress = Column(Integer, nullable=False)
    success     = Column(Integer, nullable=False)

    def __init__(self, commit_hash, distro_hash, job_id, notes, url, in_progress, success):

        self.commit_hash = commit_hash
        self.distro_hash = distro_hash
        self.job_id = job_id     
        self.notes = notes      
        self.url = url        
        self.in_progress = in_progress
        self.success = success    


    def __repr__(self):
        return "<JobResults (job_id='%s')" % self.job_id


class Promotion(Base):
    """Promotions reported to the dlrnapi.

    """

    __tablename__ = 'promotions'

    id = Column(Integer, nullable=False, unique=True, primary_key=True)

    timestamp    = Column(Integer, nullable=False)
    commit_hash  = Column(String(MAX_LEN_COMMIT_HASH), nullable=False)
    distro_hash  = Column(String(MAX_LEN_DISTRO_HASH), nullable=False)
    repo_hash    = Column(String(MAX_LEN_REPO_HASH), nullable=False)
    promote_name = Column(String(MAX_LEN_PROMOTION_LINK), nullable=False)
    user         = Column(String(MAX_LEN_USER), nullable=False)
    repo_url     = Column(String(MAX_LEN_URL), nullable=False)

# WIP
class PromotionRule(Base):
    """Ruleset for promotions, (today) from here: https://github.com/rdo-infra/ci-config/tree/master/ci-scripts/dlrnapi_promoter/config"""
    
    __tablename__ = 'promotionrules'

    id = Column(Integer, nullable=False, unique=True, primary_key=True)
   
    git_permalink_url = Column(String(MAX_LEN_URL))
    promote_target    = Column(String(MAX_LEN_PROMOTION_LINK), nullable=False)
    promote_source    = Column(String(MAX_LEN_PROMOTION_LINK), nullable=False)
    
    # TODO: this should really be stored differently, KISS for now
    job_id_csvlist    = Column(String(MAX_LEN_JOBLIST))


"""

TODO
t_promotionattempts = Table(
    'promotionattempts', metadata,
    Column('id', ForeignKey(u'promotionrules.id'), nullable=False, unique=True),
    Column('repo_hash', String, nullable=False),
    Column('distro_hash', String, nullable=False),
    Column('commit_hash', String, nullable=False),
    Column('started_time', Integer, nullable=False),
    Column('ended_time', Integer),
    Column('promotionrule_id', Integer, nullable=False),
    Column('promotion_result', Integer, nullable=False, server_default=text("0"))
)

"""


if __name__ == '__main__':
    #engine = create_engine('sqlite:///dlrnapi_promoter.db', echo=True)
    engine = create_engine('sqlite:///:memory:', echo=True)
    Base.metadata.create_all(engine)