"""Code for channel selection."""
from .utils.distance import distance
from .classification import MDM
import numpy
from sklearn.base import BaseEstimator, TransformerMixin


class ElectrodeSelection(BaseEstimator, TransformerMixin):

    """Channel selection based on a Riemannian geometry criterion.

    For each class, a centroid is estimated, and the channel selection is based
    on the maximization of the distance between centroids. This is done by a
    backward elimination where the electrode that carries the less distance is
    removed from the subset at each iteration.
    This algorith is described in [1].

    Parameters
    ----------
    nelec : int (default 16)
        the number of electrode to keep in the final subset.
    metric : string | dict (default: 'riemann')
        The type of metric used for centroid and distance estimation.
        see `mean_covariance` for the list of supported metric.
        the metric could be a dict with two keys, `mean` and `distance` in
        order to pass different metric for the centroid estimation and the
        distance estimation. Typical usecase is to pass 'logeuclid' metric for
        the mean in order to boost the computional speed and 'riemann' for the
        distance in order to keep the good sensitivity for the selection.
    n_jobs : int, (default: 1)
        The number of jobs to use for the computation. This works by computing
        each of the class centroid in parallel.
        If -1 all CPUs are used. If 1 is given, no parallel computing code is
        used at all, which is useful for debugging. For n_jobs below -1,
        (n_cpus + 1 + n_jobs) are used. Thus for n_jobs = -2, all CPUs but one
        are used.

    Attributes
    ----------
    covmeans : list
        the class centroids.
    dist : list
        list of distance at each interation.

    See Also
    --------
    Kmeans
    FgMDM

    References
    ----------
    [1] A. Barachant and S. Bonnet, "Channel selection procedure using
    riemannian distance for BCI applications," in 2011 5th International
    IEEE/EMBS Conference on Neural Engineering (NER), 2011, 348-351
    """

    def __init__(self, nelec=16, metric='riemann', n_jobs=1):
        """Init."""
        self.nelec = nelec
        self.metric = metric
        self.subelec = None
        self.n_jobs = n_jobs
        self.dist = []

    def fit(self, X, y=None, sample_weight=None):
        """Find the optimal subset of electrodes.

        Parameters
        ----------
        X : ndarray, shape (n_trials, n_channels, n_channels)
            ndarray of SPD matrices.
        y : ndarray shape (n_trials, 1)
            labels corresponding to each trial.
        sample_weight : None | ndarray shape (n_trials, 1)
            the weights of each sample. if None, each sample is treated with
            equal weights.

        Returns
        -------
        self : ElectrodeSelection instance
            The ElectrodeSelection instance.
        """
        mdm = MDM(metric=self.metric, n_jobs=self.n_jobs)
        mdm.fit(X, y, sample_weight=sample_weight)
        self.covmeans = mdm.covmeans

        Ne, _ = self.covmeans[0].shape

        self.subelec = range(0, Ne, 1)
        while (len(self.subelec)) > self.nelec:
            di = numpy.zeros((len(self.subelec), 1))
            for idx in range(len(self.subelec)):
                sub = self.subelec[:]
                sub.pop(idx)
                di[idx] = 0
                for i in range(len(self.covmeans)):
                    for j in range(i + 1, len(self.covmeans)):
                        di[idx] += distance(self.covmeans[i][:, sub][sub, :],
                                            self.covmeans[j][:, sub][sub, :],
                                            metric=mdm.metric_dist)
            # print di
            torm = di.argmax()
            self.dist.append(di.max())
            self.subelec.pop(torm)
        return self

    def transform(self, X):
        """Return reduced matrices.

        Parameters
        ----------
        X : ndarray, shape (n_trials, n_channels, n_channels)
            ndarray of SPD matrices.

        Returns
        -------
        covs : ndarray, shape (n_trials, n_elec, n_elec)
            The covariances matrices after reduction of the number of channels.
        """
        if self.subelec is None:
            self.subelec = range(0, X.shape[1], 1)
        return X[:, self.subelec, :][:, :, self.subelec]
