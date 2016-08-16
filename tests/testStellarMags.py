import unittest
import lsst.sims.utils as utils
import numpy as np

import lsst.utils.tests


def setup_module(module):
    lsst.utils.tests.init()


class StellarMagsTest(unittest.TestCase):
    """
    Test the example stellar colors code
    """

    def testSM(self):
        keys = ['O', 'B', 'A', 'F', 'G', 'K', 'M',
                'HeWD_25200_80', 'WD_11000_85', 'WD_3000_85']
        filterNames = ['u', 'g', 'r', 'i', 'z', 'y']

        # Check each type returns the correct format
        for key in keys:
            result = utils.stellarMags(key)
            for fn in filterNames:
                assert(fn in result)
                assert((isinstance(result[fn], float)) |
                       (isinstance(result[fn], np.float64)))

        # Check the exception gets raised
        self.assertRaises(ValueError, utils.stellarMags, 'ack')

        # Check the mags get fainter
        for st in keys:
            mags = utils.stellarMags(st)
            mags2 = utils.stellarMags(st, rmag=20.)
        for key in mags:
            self.assertLess(mags[key], mags2[key])


class MemoryTestClass(lsst.utils.tests.MemoryTestCase):
    pass

if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
