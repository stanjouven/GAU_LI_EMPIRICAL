"""This file contains some functions needed to estimate (via maximum
likelihood) the source of a SI epidemic process (with Gaussian edge delays).

The important function is
    s_est, likelihood = ml_estimate(graph, obs_time, sigma, is_tree, paths,
    path_lengths, max_dist)

where s_est is the list of nodes having maximum a posteriori likelihood and
likelihood is a dictionary containing the a posteriori likelihood of every
node.

"""
import math
import random
import networkx as nx
import numpy as np
import GAU_LI_EMPIRICAL.source_est_tools as tl
import operator
import collections

import scipy.stats as st
from scipy.misc import logsumexp

def ml_estimate(graph, obs_time, path_lengths, max_dist=np.inf):

    """Returns estimated source from graph and partial observation of the
    process.

    - graph is a networkx graph
    - obs_time is a dictionary containing the observervations: observer -->
      time

    Output:
    - list of nodes having maximum a posteriori likelihood
    - dictionary: node -> a posteriori likelihood

    """

    ### Gets the referential observer took at random
    sorted_obs = sorted(obs_time.items(), key=operator.itemgetter(1))
    obs_list = [x[0] for x in sorted_obs]
    random.shuffle(obs_list)
    ref_obs = obs_list[0]
    #ref_obs = random.choice(obs_list)

    ### Gets the nodes of the graph and initializes likelihood
    nodes = np.array(list(graph.nodes))
    loglikelihood = {n: -np.inf for n in nodes}

    # average the path lengths from all the diffusion
    mean_path_lengths = tl.compute_mean_shortest_path(path_lengths)

    # candidate nodes does not contain observers nodes by assumption
    candidate_nodes = np.array(list(set(nodes) - set(obs_list)))

    for s in candidate_nodes:
        ### Mean vector
        mu_s, selected_obs = tl.mu_vector_s(mean_path_lengths, s, obs_list, ref_obs)
        # covariance matrix
        cov_d_s = tl.cov_matrix(path_lengths, selected_obs, s, ref_obs)
        ### Computes log-probability of the source being the real source
        likelihood, tmp = logLH_source_tree(mu_s, cov_d_s, selected_obs, obs_time, ref_obs)
        loglikelihood[s] = likelihood




    ### Find the nodes with maximum loglikelihood and return the nodes
    # with maximum a posteriori likelihood
    ### Corrects a bias
    posterior = posterior_from_logLH(loglikelihood)

    scores = sorted(posterior.items(), key=operator.itemgetter(1), reverse=True)
    source_candidate = scores[0][0]

    return source_candidate, scores

#################################################### Helper methods for ml algo
def posterior_from_logLH(loglikelihood):
    """Computes and correct the bias associated with the loglikelihood operation.
    The output is a likelihood.

    Returns a dictionary: node -> posterior probability

    """
    bias = logsumexp(list(loglikelihood.values()))
    return dict((key, np.exp(value - bias))
            for key, value in loglikelihood.items())


def logLH_source_tree(mu_s, cov_d, obs, obs_time, ref_obs):
    """ Returns loglikelihood of node 's' being the source.
    For that, the probability of the observed time is computed in a tree where
    the current candidate is the source/root of the tree.

    - mu_s is the mean vector of Gaussian delays when s is the source
    - cov_d the covariance matrix for the tree
    - obs_time is a dictionary containing the observervations: observer --> time
    - obs is the list of observers without containing the reference observer

    """
    assert len(obs) > 1, obs

    ### Creates the vector for the infection times with respect to the referential observer
    obs_d = np.zeros((len(obs), 1))

    ### Loops over all the observers (w/o first one (referential) and last one (computation constraint))
    #   Every time it computes the infection time with respect to the ref obs
    for l in range(0, len(obs)):
        obs_d[l] = obs_time[obs[l]] - obs_time[ref_obs]

    ### Computes the log of the gaussian probability of the observed time being possible
    exponent =  - (1/2 * (obs_d - mu_s).T.dot(np.linalg.inv(cov_d)).dot(obs_d -
            mu_s))
    denom = math.sqrt((2*math.pi)**(len(obs_d)-1)*np.linalg.det(cov_d))
    return (exponent - np.log(denom))[0,0], obs_d - mu_s
