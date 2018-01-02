"""
This module implements utilities to convert between RA, Dec and indexes
on the Hierarchical Triangular Mesh (HTM), a system of tiling the unit sphere
with nested triangles.  The HTM is described in these references

Kunszt P., Szalay A., Thakar A. (2006) in "Mining The Sky",
Banday A, Zaroubi S, Bartelmann M. eds.
ESO Astrophysics Symposia
https://www.researchgate.net/publication/226072008_The_Hierarchical_Triangular_Mesh

Szalay A. et al. (2007)
"Indexing the Sphere with the Hierarchical Triangular Mesh"
arXiv:cs/0701164
"""

import numpy as np
from lsst.sims.utils import cartesianFromSpherical, sphericalFromCartesian

__all__ = ["Trixel", "HalfSpace", "findHtmid", "trixelFromHtmid",
           "basic_trixels", "halfSpaceFromRaDec", "levelFromHtmid",
           "getAllTrixels"]


class Trixel(object):
    """
    A trixel is a single triangle in the Hierarchical Triangular Mesh (HTM)
    tiling scheme.  It is defined by its three corners on the unit sphere.

    Instantiating this class directly is a bad idea. __init__() does nothing
    to ensure that the parameters you give it are self-consistent.  Instead,
    use the trixelFromHtmid() or getAllTrixels() methods in this module
    to instantiate trixels.
    """

    def __init__(self, present_htmid, present_corners):
        """
        Initialize the current Trixel

        Parameters
        ----------
        present_htmid is the htmid of this Trixel

        present_corners is a numpy array.  Each row
        contains the Cartesian coordinates of one of
        this Trixel's corners.

        WARNING
        -------
        No effort is made to ensure that the parameters
        passed in are self consistent.  You should probably
        not being calling __init__() directly.  Use the
        trixelFromHtmid() or getAllTrixels() methods to
        instantiate trixels.
        """
        self._corners = present_corners
        self._htmid = present_htmid
        self._level = (len('{0:b}'.format(self._htmid))/2)-1
        self._cross01 = None
        self._cross12 = None
        self._cross20 = None
        self._w_arr = None
        self._bounding_circle = None

    def __eq__(self, other):

        tol = 1.0e-20

        if self._htmid == other._htmid:
            if self._level == other._level:
                if np.allclose(self._corners, other._corners, atol=tol):
                    return True

        return False

    def __ne__(self, other):
        return not (self==other)

    @property
    def htmid(self):
        """
        The unique integer identifying this trixel.
        """
        return self._htmid

    def contains(self, ra, dec):
        """
        Returns True if the specified RA, Dec are
        inside this trixel; False if not.

        RA and Dec are in degrees.
        """
        xyz = cartesianFromSpherical(np.radians(ra), np.radians(dec))
        return self.contains_pt(xyz)

    @property
    def cross01(self):
        """
        The cross product of the unit vectors defining
        the zeroth and first corners of this trixel.
        """
        if self._cross01 is None:
            self._cross01 = np.cross(self._corners[0], self._corners[1])
        return self._cross01

    @property
    def cross12(self):
        """
        The cross product of the unit vectors defining
        the first and second corners of this trixel.
        """
        if self._cross12 is None:
            self._cross12 = np.cross(self._corners[1], self._corners[2])
        return self._cross12

    @property
    def cross20(self):
        """
        The cross product of the unit vectors defining the second
        and zeroth corners of this trixel.
        """
        if self._cross20 is None:
            self._cross20 = np.cross(self._corners[2], self._corners[0])
        return self._cross20

    def _contains_one_pt(self, pt):
        """
        pt is a Cartesian point (not necessarily on the unit sphere).

        Returns True if the point projected onto the unit sphere
        is contained within this trixel; False if not.

        See equation 5 of

        Kunszt P., Szalay A., Thakar A. (2006) in "Mining The Sky",
        Banday A, Zaroubi S, Bartelmann M. eds.
        ESO Astrophysics Symposia
        https://www.researchgate.net/publication/226072008_The_Hierarchical_Triangular_Mesh
        """
        if np.dot(self.cross01,pt)>=0.0:
            if np.dot(self.cross12, pt)>=0.0:
                if np.dot(self.cross20, pt)>=0.0:
                    return True

        return False

    def _contains_many_pts(self, pts):
        """
        pts is an array of Cartesian points (pts[0] is the zeroth
        point, pts[1] is the first point, etc.; not necessarily on
        the unit sphere).

        Returns an array of booleans denoting whether or not the
        projection of each point onto the unit sphere is contained
        within this trixel.

        See equation 5 of

        Kunszt P., Szalay A., Thakar A. (2006) in "Mining The Sky",
        Banday A, Zaroubi S, Bartelmann M. eds.
        ESO Astrophysics Symposia
        https://www.researchgate.net/publication/226072008_The_Hierarchical_Triangular_Mesh
        """
        return np.where(np.logical_and(np.dot(pts, self.cross01) >= 0.0,
                        np.logical_and(np.dot(pts, self.cross12) >= 0.0,
                                       np.dot(pts, self.cross20) >= 0.0)),
                        True, False)

    def contains_pt(self, pt):
        """
        pt is either a single Cartesian point
        or an array of Cartesian points (pt[0]
        is the zeroth point, pt[1] is the first
        point, etc.).

        Return a boolean or array of booleans
        denoting whether this point(s) projected
        onto the unit sphere is/are contained within
        the current trixel.
        """
        if len(pt.shape) == 1:
            return self._contains_one_pt(pt)
        return self._contains_many_pts(pt)

    def _create_w(self):

        w0 = self._corners[1]+self._corners[2]
        w0 = w0/np.sqrt(np.power(w0, 2).sum())
        w1 = self._corners[0]+self._corners[2]
        w1 = w1/np.sqrt(np.power(w1, 2).sum())
        w2 = self._corners[0]+self._corners[1]
        w2 = w2/np.sqrt(np.power(w2, 2).sum())

        self._w_arr = [w0, w1, w2]

    @property
    def w_arr(self):
        """
        An array of vectors needed to define the child trixels
        of this trixel.  See equation (3) of

        Kunszt P., Szalay A., Thakar A. (2006) in "Mining The Sky",
        Banday A, Zaroubi S, Bartelmann M. eds.
        ESO Astrophysics Symposia
        httpd://www.researchgate.net/publication/226072008_The_Hierarchical_Triangular_Mesh
        """
        if self._w_arr is None:
            self._create_w()
        return self._w_arr

    @property
    def t0(self):
        """
        The zeroth child trixel of this trixel.

        See Figure 2 of

        Szalay A. et al. (2007)
        "Indexing the Sphere with the Hierarchical Triangular Mesh"
        arXiv:cs/0701164
        """
        if not hasattr(self, '_t0'):
            self._t0 = Trixel(self.htmid<<2, [self._corners[0], self.w_arr[2], self.w_arr[1]])
        return self._t0

    @property
    def t1(self):
        """
        The first child trixel of this trixel.

        See Figure 2 of

        Szalay A. et al. (2007)
        "Indexing the Sphere with the Hierarchical Triangular Mesh"
        arXiv:cs/0701164
        """
        if not hasattr(self, '_t1'):
           self._t1 = Trixel((self.htmid<<2)+1, [self._corners[1], self.w_arr[0],self.w_arr[2]])
        return self._t1

    @property
    def t2(self):
        """
        The second child trixel of this trixel.

        See Figure 2 of

        Szalay A. et al. (2007)
        "Indexing the Sphere with the Hierarchical Triangular Mesh"
        arXiv:cs/0701164
        """
        if not hasattr(self, '_t2'):
            self._t2 = Trixel((self.htmid<<2)+2, [self._corners[2], self.w_arr[1],self.w_arr[0]])
        return self._t2

    @property
    def t3(self):
        """
        The third child trixel of this trixel.

        See Figure 2 of

        Szalay A. et al. (2007)
        "Indexing the Sphere with the Hierarchical Triangular Mesh"
        arXiv:cs/0701164
        """
        if not hasattr(self, '_t3'):
            self._t3 = Trixel((self.htmid<<2)+3, [self.w_arr[0], self.w_arr[1], self.w_arr[2]])
        return self._t3

    def get_children(self):
        """
        Return a list of all of the child trixels of this trixel.
        """
        return [self.t0, self.t1, self.t2, self.t3]

    def get_child(self, dex):
        """
        Return a specific child trixel of this trixel.

        dex is an integer in the range [0,3] denoting
        which child to return

        See Figure 1 of

        Kunszt P., Szalay A., Thakar A. (2006) in "Mining The Sky",
        Banday A, Zaroubi S, Bartelmann M. eds.
        ESO Astrophysics Symposia
        https://www.researchgate.net/publication/226072008_The_Hierarchical_Triangular_Mesh

        for an explanation of which trixel corresponds to whic
        index.
        """
        if dex==0:
            return self.t0
        elif dex==1:
            return self.t1
        elif dex==2:
            return self.t2
        elif dex==3:
            return self.t3
        else:
            raise RuntimeError("Trixel has no %d child" % dex)

    def get_center(self):
        """
        Return the RA, Dec of the center of the circle bounding
        this trixel (RA, Dec both in degrees)
        """
        ra, dec =sphericalFromCartesian(self.bounding_circle[0])
        return np.degrees(ra), np.degrees(dec)

    def get_radius(self):
        """
        Return the angular radius in degrees of the circle bounding
        this trixel.
        """
        return np.degrees(self.bounding_circle[2])

    @property
    def level(self):
        """
        Return the level of subdivision for this trixel.  A higher
        level means a finer subdivision of the unit sphere and smaller
        trixels.  What we refer to as 'level' is denoted by 'd' in
        equation 2.5 of

        Szalay A. et al. (2007)
        "Indexing the Sphere with the Hierarchical Triangular Mesh"
        arXiv:cs/0701164

        For a given level == ell, there are 8*4**(ell-1) trixels in
        the entire unit sphere.

        The htmid values of trixels with level==ell will consist
        of 4 + 2*(ell-1) bits
        """
        return self._level

    @property
    def corners(self):
        return self._corners

    @property
    def bounding_circle(self):
        """
        The circle on the unit sphere that bounds this trixel.

        See equation 4.2 of

        Szalay A. et al. (2007)
        "Indexing the Sphere with the Hierarchical Triangular Mesh"
        arXiv:cs/0701164

        Returns
        -------
        A tuple:
            Zeroth element is the unit vector pointing at
            the center of the bounding circle

            First element is the distance from the center of
            the unit sphere to the plane of the bounding circle
            (i.e. the dot product of the zeroth element with the
            most distant corner of the trixel).

            Second element is the half angular extent of the bounding circle.
        """
        if self._bounding_circle is None:
            # find the unit vector pointing to the center of the trixel
            vb = np.cross((self._corners[1]-self._corners[0]), (self._corners[2]-self._corners[1]))
            vb = vb/np.sqrt(np.power(vb, 2).sum())

            # find the distance from the center of the trixel
            # to the most distant corner of the trixel
            dd = np.dot(self.corners,vb).max()

            if np.abs(dd)>1.0:
                raise RuntimeError("Bounding circle has dd %e (should be between -1 and 1)" % dd)

            self._bounding_circle = (vb, dd, np.arccos(dd))

        return self._bounding_circle

# Below are defined the initial Trixels
#
# See equations (1) and (2) of
#
# Kunszt P., Szalay A., Thakar A. (2006) in "Mining The Sky",
# Banday A, Zaroubi S, Bartelmann M. eds.
# ESO Astrophysics Symposia
# https://www.researchgate.net/publication/226072008_The_Hierarchical_Triangular_Mesh

_N0_trixel = Trixel(12, [np.array([1.0, 0.0, 0.0]),
                         np.array([0.0, 0.0, 1.0]),
                         np.array([0.0, -1.0, 0.0])])

_N1_trixel = Trixel(13,[np.array([0.0, -1.0, 0.0]),
                        np.array([0.0, 0.0, 1.0]),
                        np.array([-1.0, 0.0, 0.0])])

_N2_trixel = Trixel(14, [np.array([-1.0, 0.0, 0.0]),
                         np.array([0.0, 0.0, 1.0]),
                         np.array([0.0, 1.0, 0.0])])

_N3_trixel = Trixel(15, [np.array([0.0, 1.0, 0.0]),
                         np.array([0.0, 0.0, 1.0]),
                         np.array([1.0, 0.0, 0.0])])

_S0_trixel = Trixel(8, [np.array([1.0, 0.0, 0.0]),
                        np.array([0.0, 0.0, -1.0]),
                        np.array([0.0, 1.0, 0.0])])

_S1_trixel = Trixel(9, [np.array([0.0, 1.0, 0.0]),
                        np.array([0.0, 0.0, -1.0]),
                        np.array([-1.0, 0.0, 0.0])])

_S2_trixel = Trixel(10, [np.array([-1.0, 0.0, 0.0]),
                         np.array([0.0, 0.0, -1.0]),
                         np.array([0.0, -1.0, 0.0])])

_S3_trixel = Trixel(11, [np.array([0.0, -1.0, 0.0]),
                         np.array([0.0, 0.0, -1.0]),
                         np.array([1.0, 0.0, 0.0])])

basic_trixels = {'N0': _N0_trixel,
                 'N1': _N1_trixel,
                 'N2': _N2_trixel,
                 'N3': _N3_trixel,
                 'S0': _S0_trixel,
                 'S1': _S1_trixel,
                 'S2': _S2_trixel,
                 'S3': _S3_trixel}


def levelFromHtmid(htmid):
    """
    Find the level of a trixel from its htmid.  The level
    indicates how refined the triangular mesh is.

    There are 8*4**(d-1) triangles in a mes of level=d

    (equation 2.5 of
    Szalay A. et al. (2007)
    "Indexing the Sphere with the Hierarchical Triangular Mesh"
    arXiv:cs/0701164)
    """
    htmid_copy = htmid
    i_level = -1
    while htmid_copy != 0:
        htmid_copy >>= 2
        i_level += 1
    return i_level

def trixelFromHtmid(htmid):
    """
    Return the trixel corresponding to the given htmid
    (htmid is the unique integer identifying each trixel).

    Note: this method is not efficient for finding many
    trixels.  It recursively generates trixels and their
    children until it finds the right htmid without
    remembering which trixels it has already generated.
    To generate many trixels, use the getAllTrixels()
    method, which efficiently generates all of the trixels
    up to a given mesh level.
    """
    level = levelFromHtmid(htmid)
    base_htmid = htmid>>2*(level-1)

    ans = None

    if base_htmid == 8:
        ans = _S0_trixel
    elif base_htmid == 9:
        ans = _S1_trixel
    elif base_htmid == 10:
        ans = _S2_trixel
    elif base_htmid == 11:
        ans = _S3_trixel
    elif base_htmid == 12:
        ans = _N0_trixel
    elif base_htmid == 13:
        ans = _N1_trixel
    elif base_htmid == 14:
        ans = _N2_trixel
    elif base_htmid == 15:
        ans = _N3_trixel

    if ans is None:
        raise RuntimeError("Unable to find trixel for id %d" % htmid)

    if level == 1:
        return ans

    complement = 3
    complement <<= 2*(level-2)

    for ix in range(level-1):
        target = htmid&complement
        target >>= 2*(level-ix-2)
        if target>=4:
            raise RuntimeError("target %d" % target)
        ans = ans.get_child(target)
        complement >>= 2

    return ans

def getAllTrixels(level):
    """
    Return a dict of all of the trixels up to a given mesh level.
    The dict is keyed on htmid, unique integer identifying
    each trixel on the unit sphere.  This method is efficient
    at generating many trixels at once.
    """

    n_bits_added = 2*(level-1)

    start_trixels = range(8,16)
    trixel_dict = {}
    for t0 in start_trixels:
        trix0 = trixelFromHtmid(t0)
        trixel_dict[t0] = trix0

    ct = 0
    for t0 in start_trixels:
        t0 = t0 << n_bits_added
        for dt in range(2**n_bits_added):
            htmid = t0 + dt
            ct += 1
            if htmid in trixel_dict:
                continue

            parent_id = htmid >> 2

            while parent_id not in trixel_dict:
                for n_right in range(2,n_bits_added,2):
                    if htmid >> n_right in trixel_dict:
                        break
                to_gen = htmid >> n_right
                if to_gen in trixel_dict:
                    trix0 = trixel_dict[to_gen]
                else:
                    trix0= trixelFromHtmid(to_gen)
                    trixel_dict[to_gen] = trix0

                trixel_dict[to_gen<<2] = trix0.get_child(0)
                trixel_dict[(to_gen<<2)+1] = trix0.get_child(1)
                trixel_dict[(to_gen<<2)+2] = trix0.get_child(2)
                trixel_dict[(to_gen<<2)+3] = trix0.get_child(3)

            trix0 = trixel_dict[parent_id]
            trixel_dict[(parent_id<<2)] = trix0.get_child(0)
            trixel_dict[(parent_id<<2)+1] = trix0.get_child(1)
            trixel_dict[(parent_id<<2)+2] = trix0.get_child(2)
            trixel_dict[(parent_id<<2)+3] = trix0.get_child(3)

    return trixel_dict

def _iterateTrixelFinder(pt, parent, max_level):
    children = parent.get_children()
    for child in children:
        if child.contains_pt(pt):
            if child.level == max_level:
                return child.htmid
            else:
                return _iterateTrixelFinder(pt, child, max_level)

def findHtmid(ra, dec, max_level):
    """
    Find the htmid (the unique integer identifying
    each trixel) of the trixel containing a given
    RA, Dec pair.

    Parameters
    ----------
    ra in degrees

    dec in degrees

    max_level is an integer denoting the mesh level
    of the trixel you want found

    Note: This method only works one point at a time.
    It cannot take arrays of RA and Dec.

    Returns
    -------
    An int (the htmid)
    """

    raRad = np.radians(ra)
    decRad = np.radians(dec)
    pt = cartesianFromSpherical(raRad, decRad)

    if _S0_trixel.contains_pt(pt):
        parent = _S0_trixel
    elif _S1_trixel.contains_pt(pt):
        parent = _S1_trixel
    elif _S2_trixel.contains_pt(pt):
        parent = _S2_trixel
    elif _S3_trixel.contains_pt(pt):
        parent = _S3_trixel
    elif _N0_trixel.contains_pt(pt):
        parent = _N0_trixel
    elif _N1_trixel.contains_pt(pt):
        parent = _N1_trixel
    elif _N2_trixel.contains_pt(pt):
        parent = _N2_trixel
    elif _N3_trixel.contains_pt(pt):
        parent = _N3_trixel
    else:
        raise RuntimeError("could not find parent Trixel")

    return _iterateTrixelFinder(pt, parent, max_level)


class HalfSpace(object):
    """
    HalfSpaces are circles on the unit sphere defined by intersecting
    a plane with the unit sphere.  They are specified by the unit vector
    pointing to their center on the unit sphere and the distance from
    the center of the unit sphere to the plane along that unit vector.

    See Section 3.1 of

    Szalay A. et al. (2007)
    "Indexing the Sphere with the Hierarchical Triangular Mesh"
    arXiv:cs/0701164

    Note that the specifying distance can be negative.  In this case,
    the halfspace is defined as the larger of the two regions on the
    unit sphere divided by the circle where the plane of the halfspace
    intersects the unit sphere.
    """

    def __init__(self, vector, length):
        """
        Parameters
        ----------
        vector is the unit vector pointing to the center of
        the halfspace on the unit sphere

        length is the distance from the center of the unit
        sphere to theplane defining the half space along
        vector.  This length can be negative, in which case,
        the halfspace is defined as the larger of the two
        regions on the unit sphere divided by the circle
        where the plane of the halfspace intersects the
        unit sphere.
        """
        self._v = vector/np.sqrt(np.power(vector, 2).sum())
        self._d = length
        if np.abs(self._d)<1.0:
            self._phi = np.arccos(self._d)  # half angular extent of the half space
        else:
            if self._d > 0.0:
                self._phi = np.pi
            else:
                self._phi = 0.0

    def __eq__(self, other):
        tol = 1.0e-10
        if np.abs(self.dd-other.dd)>tol:
            return False
        if np.abs(np.dot(self.vector, other.vector)-1.0)>tol:
            return False
        return True

    @property
    def vector(self):
        """
        The unit vector from the origin to the center of the Half Space.
        """
        return self._v

    @property
    def dd(self):
        """
        The distance along the Half Space's vector that defines the
        extent of the Half Space.
        """
        return self._d

    @property
    def phi(self):
        """
        The angular radius of the Half Space on the surface of the sphere
        in radians.
        """
        return self._phi

    def contains_pt(self, pt):
        """
        pt is a cartesian point (not necessarily on
        the unit sphere).  The method returns True if
        the projection of that point onto the unit sphere
        is contained in the halfspace; False otherwise.
        """
        norm_pt = pt/np.sqrt(np.power(pt, 2).sum())

        dot_product = np.dot(pt, self._v)

        if dot_product > self._d:
            return True

        return False

    def intersects_edge(self, pt1, pt2):
        """
        pt1 and pt2 are two unit vectors; the edge goes from pt1 to pt2.
        Return True if the edge intersects this halfspace; False otherwise.

        see equation 4.8 of

        Szalay A. et al. (2007)
        "Indexing the Sphere with the Hierarchical Triangular Mesh"
        arXiv:cs/0701164
        """
        costheta = np.dot(pt1, pt2)
        u=np.sqrt((1-costheta)/(1+costheta))  # using trig identity for tan(theta/2)
        gamma1 = np.dot(self._v, pt1)
        gamma2 = np.dot(self._v, pt2)
        b = gamma1*(u*u-1.0) + gamma2*(u*u+1)
        a = -u*u*(gamma1+self._d)
        c = gamma1 - self._d

        det = b*b - 4*a*c
        if det<0.0:
            return False

        sqrt_det = np.sqrt(det)
        pos = (-b + sqrt_det)/(2.0*a)

        if pos >= 0.0 and pos <= 1.0:
            return True

        neg = (-b - sqrt_det)/(2.0*a)
        if neg >= 0.0 and neg <= 1.0:
            return True

        return False

    def intersects_bounding_circle(self, tx):
        """
        tx is a Trixel.  Return True if this halfspace intersects
        the bounding circle of the trixel; False otherwise.

        See the discussion around equation 4.2 of

        Szalay A. et al. (2007)
        "Indexing the Sphere with the Hierarchical Triangular Mesh"
        arXiv:cs/0701164
        """

        dotproduct = np.dot(tx.bounding_circle[0], self._v)
        if np.abs(dotproduct) < 1.0:
            theta = np.arccos(np.dot(tx.bounding_circle[0], self._v))
        elif dotproduct<1.000000001:
            theta = 0.0
        elif dotproduct>-1.000000001:
            theta = np.pi
        else:
            raise RuntimeError("Dot product between unit vectors is %e" % dotproduct)

        if theta > self._phi + tx.bounding_circle[2]:
            return False

        return True

    def contains_trixel(self, tx):
        """
        tx is a Trixel.

        Return "full" if the Trixel is fully contained by
        this halfspace.

        Return "partial" if the Trixel is only partially
        contained by this halfspace

        Return "outside" if no part of the Trixel is
        contained by this halfspace.

        See section 4.1 of

        Szalay A. et al. (2007)
        "Indexing the Sphere with the Hierarchical Triangular Mesh"
        arXiv:cs/0701164
        """

        n_corners_contained = 0
        for corner in tx.corners:
            if self.contains_pt(corner):
                n_corners_contained += 1

        if n_corners_contained == 3:
            return "full"
        elif n_corners_contained > 0:
            return "partial"

        # check if the trixel's bounding circle intersects
        # the halfspace
        if not self.intersects_bounding_circle(tx):
            return "outside"

        # need to test that the bounding circle intersect the halfspace
        # boundary

        intersection = False
        for edge in ((tx.corners[0], tx.corners[1]),
                     (tx.corners[1], tx.corners[2]),
                     (tx.corners[2], tx.corners[0])):

            if self.intersects_edge(edge[0], edge[1]):
                intersection = True
                break

        if intersection:
            return "partial"

        if tx.contains_pt(self._v):
            return "partial"

        return "outside"

    def findAllTrixels(self, level):
        """
        Find the HTMIDs of all of the trixels filling the half space

        Parameters
        ----------
        level is an integer denoting the resolution of the trixel grid

        Returns
        -------
        A list of tuples.  Each tuple gives an inclusive range of HTMIDs
        corresponding to trixels within the HalfSpace
        """

        global basic_trixels

        active_trixels = []
        for trixel_name in basic_trixels:
            active_trixels.append(basic_trixels[trixel_name])

        n_full = 0
        n_partial = 0
        n_outside = 0

        output_prelim = []
        max_d_htmid = 0

        # Once we establish that a given trixel is completely
        # contained within a the HalfSpace, we will need to
        # convert that trixel into a (min_htmid, max_htmid) pair.
        # This will involve evolving up from the current level
        # of trixel resolution to the desired level of trixel
        # resolution, setting the resulting 2-bit pairs to 0 for
        # min_htmid and 3 for max_htmid.  We can get min_htmid by
        # taking the base trixel's level and multiplying by an
        # appropriate power of 2.  We can get max_htmid by adding
        # an integer that, in binary, is wholly comprised of 1s
        # to min_htmid.  Here we construct that integer of 1s,
        # starting out at level-2, since the first trixels
        # to which we will need to add max_d_htmid will be
        # at least at level 2 (the children of the base trixels).
        for ii in range(level-2):
            max_d_htmid += 3
            max_d_htmid <<= 2

        # start iterating at level 2 because level 1 is the base trixels,
        # where we are already starting, and i_level reallly refers to
        # the level of the child trixels we are investigating
        for i_level in range(2,level):
            max_d_htmid >>= 2

            new_active_trixels = []
            for tt in active_trixels:
                children = tt.get_children()
                for child in children:
                    is_contained = self.contains_trixel(child)
                    if is_contained == 'partial':
                        n_partial += 1
                        # need to investigate more fully
                        new_active_trixels.append(child)
                    elif is_contained == 'full':
                        n_full += 1
                        # all of this trixels children, and their children are contained
                        min_htmid = child._htmid << 2*(level-i_level)
                        max_htmid = min_htmid
                        max_htmid += max_d_htmid
                        output_prelim.append((min_htmid, max_htmid))

                        ########################################
                        # some assertions for debugging purposes
                        #assert min_htmid<max_htmid
                        #try:
                        #    test_trix = trixelFromHtmid(min_htmid)
                        #    assert self.contains_trixel(test_trix) != 'outside'
                        #    test_trix = trixelFromHtmid(max_htmid)
                        #    assert self.contains_trixel(test_trix) != 'outside'
                        #except AssertionError:
                        #    print('is_contained %s' % is_contained)
                        #    print('level %d' % levelFromHtmid(tt._htmid))
                        #    raise
                    else:
                        n_outside += 1
                active_trixels = new_active_trixels
            if len(active_trixels) == 0:
                break

        # final pass over the active_trixels to see which of their
        # children are inside this HalfSpace
        for trix in active_trixels:
            for child in trix.get_children():
               assert levelFromHtmid(child._htmid) == level
               if self.contains_trixel(child) != 'outside':
                   output_prelim.append((child._htmid, child._htmid))

        # sort output by htmid_min
        min_dex_arr = []
        for oo in output_prelim:
            min_dex_arr.append(oo[0])
        min_dex_arr = np.argsort(min_dex_arr)
        output = []
        for ii in min_dex_arr:
            output.append(output_prelim[ii])

        return output


def halfSpaceFromRaDec(ra, dec, radius):
    """
    Take an RA, Dec and radius of a circular field of view and return
    a HalfSpace

    Parameters
    ----------
    ra in degrees

    dec in degrees

    radius in degrees

    Returns
    -------
    HalfSpace corresponding to the circular field of view
    """
    dd = np.cos(np.radians(radius))
    xyz = cartesianFromSpherical(np.radians(ra), np.radians(dec))
    return HalfSpace(xyz, dd)
