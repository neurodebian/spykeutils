""" Functions for estimating the rate instantaneous rate of neurons from
spike trains.
"""

from __future__ import division

import scipy as sp
from scipy.spatial.distance import cdist
import quantities as pq

from spykeutils.progress_indicator import ProgressIndicator

def get_refperiod_violations(spike_trains, refperiod,
                             progress=ProgressIndicator()):
    """ Return the refractory period violations in the given spike trains
    for the specified refractory period.

    :param dict spike_trains: Dictionary of lists of `SpikeTrain` objects,
        indexed by unit.
    :param refperiod: The refractory period (time).
    :type refperiod: Quantity scalar
    :param progress: A `ProgressIndicator` object for the operation.
    :type progress: :class:`spykeutils.progress_indicator.ProgressIndicator`
    :returns: Two values:

        * The total number of violations.
        * A dictionary (with the same indices as `spike_trains`) of
          lists with violation times (Quantity 1D with the same unit as
          `refperiod`) for each spike train.
    :rtype: int, dict """

    if type(refperiod) != pq.Quantity or \
       refperiod.simplified.dimensionality != pq.s.dimensionality:
        raise ValueError('refperiod must be a time quantity!')

    total_violations = 0
    violations = {}
    for u, tL in spike_trains.iteritems():
        violations[u] = []
        for i,t in enumerate(tL):
            st = t.copy()
            st.sort()
            isi = sp.diff(st)

            violations[u].append(st[isi < refperiod].rescale(refperiod.units))
            total_violations += len(violations[u][i])

            progress.step()

    return total_violations, violations

def calculate_refperiod_fp(num_spikes, refperiod, violations, total_time):
    """ Return the rate of false positives calculated from refractory period
    calculations for each unit. The equation used is described in
    (Hill et al. The Journal of Neuroscience. 2011)

    :param dict num_spikes: Dictionary of total number of spikes,
        indexed by unit.
    :param refperiod: The refractory period (time). If the spike sorting
        algorithm includes a censored period (a time after a spike during
        which no new spikes can be found), subtract it from the refractory
        period before passing it to this function.
    :type refperiod: Quantity scalar
    :param dict violations: Dictionary of total number of violations,
        indexed by unit.

    :returns: A dictionary of false positive rates indexed by unit.
        Note that values above 0.5 can not be directly interpreted as a
        false positive rate! These very high values can e.g. indicate
        that the chosen refractory period was too large.
    """
    if type(refperiod) != pq.Quantity or \
       refperiod.simplified.dimensionality != pq.s.dimensionality:
        raise ValueError('refperiod must be a time quantity!')

    fp = {}
    factor = total_time / (2 * refperiod)
    for u,n in num_spikes.iteritems():
        if n == 0:
            fp[u] = 0
            continue
        zw = (violations[u] * factor / n**2).simplified

        if zw > 0.25:
            fp[u] = 0.5 + sp.sqrt(0.25 - zw).imag
            continue
        fp[u] = 0.5 - sp.sqrt(0.25 - zw)

    return fp

def calculate_overlap_fp_fn(templates, spikes):
    """ Return a dict of tuples (False positive rate, false negative rate)
    indexed by unit. Details for the calculation can be found in
    (Hill et al. The Journal of Neuroscience. 2011). This function works on
    prewhitened data, which means it assumes that all clusters have a uniform
    normal distribution. Data can be prewhitened using the noise covariance
    matrix.

    The calculation for total false positive and false negative rates does
    not follow (Hill et al. The Journal of Neuroscience. 2011), where a
    simple addition of pairwise probabilities is proposed. Instead, the
    total error probabilities are estimated using all clusters at once.

    :param dict templates: Dictionary of prewhitened templates (cluster means)
        as numpy arrays for all units.
    :param dict spikes: Dictionary of lists of prewhitened spike waveforms
        as numpy arrays for all units.
    :returns: Two values:

        * A dictionary (indexed by unit of total
          (false positives, false negatives) tuples.
        * A dictionary of dictionaries, both indexed by units,
          of pairwise (false positives, false negatives) tuples.
    :rtype: dict, dict
    """
    units = templates.keys()
    prior = {}
    total_spikes = 0
    for u, mean in templates.iteritems():
        total_spikes += len(spikes[u])

    false_positive = {}
    false_negative = {}
    for u, s in spikes.iteritems():
        prior[u] = len(s) / total_spikes
        false_positive[u] = 0
        false_negative[u] = 0

    # Arrays of unnormalized posteriors (likelihood times prior)
    # for all units
    posterior = {}

    # Calculate posteriors
    for u1 in units[:]:
        if not spikes[u1]:
            units.remove(u1)
            continue
        posterior[u1] = {}
        for u2, mean in templates.iteritems():
            llh = _multi_norm(sp.array(spikes[u1]), mean)
            posterior[u1][u2] = llh*prior[u2]

    # Calculate pairwise false positives/negatives
    singles = {u:{} for u in units}
    for i, u1 in enumerate(units):
        u1 = units[i]
        for u2 in units[i+1:]:
            f1 = sp.sum(posterior[u1][u2] /
                        (posterior[u1][u1] + posterior[u1][u2]),
                dtype=sp.double)
            #false_positive[u1] += f1
            #false_negative[u2] += f1

            f2 = sp.sum(posterior[u2][u1] /
                        (posterior[u2][u1] + posterior[u2][u2]),
                dtype=sp.double)
            #false_negative[u1] += f2
            #false_positive[u2] += f1

            singles[u1][u2] = (f1 / len(spikes[u1]) if spikes[u1] else 0,
                               f2 / len(spikes[u1]) if spikes[u1] else 0)
            singles[u2][u1] = (f2 / len(spikes[u2]) if spikes[u2] else 0,
                               f1 / len(spikes[u2]) if spikes[u2] else 0)

    # Calculate complete false positives/negatives with extended bayes
    for u1 in units:
        numerator = posterior[u1][u1]
        normalizer = sum(posterior[u1][u2] for u2 in units)
        false_positive[u1] = sp.sum((normalizer-numerator)/normalizer)

        other_units = units[:]
        other_units.remove(u1)
        numerator = sp.vstack((posterior[u][u1] for u in other_units))
        normalizer = sp.vstack(sum(posterior[u][u2] for u2 in units) for u in other_units)
        false_negative[u1] = sp.sum(numerator/normalizer)

    # Prepare return values, convert sums to means
    totals = {}
    for u,fp in false_positive.iteritems():
        fn = false_negative[u]
        if not spikes[u]:
            totals[u] = (0,0)
        else:
            num = len(spikes[u])
            totals[u] = (fp / num, fn / num)
    return totals, singles

def _multi_norm(x, mean):
    """ Evaluate pdf of multivariate normal distribution with a mean
        at rows of x with high precision.
    """
    d = x.shape[1]
    fac = (2*sp.pi) ** (-d/2.0)
    y = cdist(x, sp.atleast_2d(mean), 'sqeuclidean') * -0.5

    return fac * sp.exp(sp.longdouble(y))

if __name__ == '__main__':
    import matplotlib.pyplot as plt

    sp.random.seed(123)
    dimension = 3
    offset = sp.zeros((dimension,1))
    offset[0] = 4
    cluster1 = sp.randn(dimension,10)
    cluster2 = sp.randn(dimension,100) + offset
    #cluster3 = sp.randn(dimension,500) + offset


    clusterList1 = [cluster1[:,i] for i in xrange(sp.size(cluster1,1))]
    clusterList2 = [cluster2[:,i] for i in xrange(sp.size(cluster2,1))]
    #clusterList3 = [cluster3[:,i] for i in xrange(sp.size(cluster3,1))]

    f, f2 = calculate_overlap_fp_fn({1: sp.zeros(dimension),
                                   2: offset.flatten()},
            {1:clusterList1, 2:clusterList2})
    print f[1]
    print f[2]
    print f2[1]
    print f2[2]
    #print f[3]

    plt.scatter(cluster1[0,:], cluster1[1,:], c='b')
    plt.scatter(cluster2[0,:], cluster2[1,:], c='g')
    #plt.scatter(cluster3[0,:], cluster3[1,:], c='r')
    plt.show()