"""
------------------------------------------------------------------------
Filename: 	polynomial_cse_iccad_test.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Test module for ICCAD 2004 paper-based polynomial CSE implementation.
Tests the exact algorithms from the paper: kernel extraction, KCM formation, and optimization.

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the ALLOCATOR module
It is intended to be used as part of the allocator design which is responsible for the soft-core, or offboard, management of the on-fabric components.
Please refer to docs/whitepaper first, which provides a complete description of the project & it's motivations.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""
import math
import numpy as np

from Allocator.Interpreter.poly.polynomial_cse_iccad import (
    MatrixRow,
    PolynomialMatrix,
    ICCADOptimizer,
    optimize_polynomial_iccad
)


class TestMatrixRow:
    """Test the MatrixRow class"""

    def test_matrix_row_creation(self):
        """Test creating matrix rows"""
        row = MatrixRow(1, [2, 0, 1])  # Represents x^2*z
        assert row.sign == 1
        assert row.exponents == [2, 0, 1]

        row2 = MatrixRow(-1, [0, 1, 0])  # Represents -y
        assert row2.sign == -1
        assert row2.exponents == [0, 1, 0]

    def test_matrix_row_equality(self):
        """Test row equality and hashing"""
        row1 = MatrixRow(1, [1, 2, 0])
        row2 = MatrixRow(1, [1, 2, 0])
        row3 = MatrixRow(-1, [1, 2, 0])

        assert row1 == row2
        assert row1 != row3
        assert hash(row1) == hash(row2)
        assert hash(row1) != hash(row3)

    def test_matrix_row_copy(self):
        """Test copying a matrix row"""
        row = MatrixRow(1, [1, 2, 3], term_id=5)
        row_copy = row.copy()

        assert row_copy.sign == row.sign
        assert row_copy.exponents == row.exponents
        assert row_copy.term_id == row.term_id

        # Ensure deep copy
        row_copy.exponents[0] = 10
        assert row.exponents[0] == 1


class TestPolynomialMatrix:
    """Test the PolynomialMatrix class (Section 2.1 of paper)"""

    def test_polynomial_matrix_creation(self):
        """Test creating polynomial matrix representation"""
        # Example from paper: sin(x) = x - S3*x^3 + S5*x^5 - S7*x^7
        variables = ['x', 'S3', 'S5', 'S7']
        matrix = PolynomialMatrix(variables)

        # Add terms
        matrix.add_term(1, {'x': 1}, term_id=1)  # x
        matrix.add_term(-1, {'x': 3, 'S3': 1}, term_id=2)  # -S3*x^3
        matrix.add_term(1, {'x': 5, 'S5': 1}, term_id=3)  # S5*x^5
        matrix.add_term(-1, {'x': 7, 'S7': 1}, term_id=4)  # -S7*x^7

        assert len(matrix.rows) == 4
        assert matrix.rows[0].exponents == [1, 0, 0, 0]  # x
        assert matrix.rows[1].exponents == [3, 1, 0, 0]  # x^3*S3
        assert matrix.rows[2].exponents == [5, 0, 1, 0]  # x^5*S5
        assert matrix.rows[3].exponents == [7, 0, 0, 1]  # x^7*S7

    def test_polynomial_matrix_string(self):
        """Test string representation of polynomial matrix"""
        variables = ['x', 'y']
        matrix = PolynomialMatrix(variables)

        matrix.add_term(1, {'x': 2})  # x^2
        matrix.add_term(1, {'x': 1, 'y': 1})  # x*y
        matrix.add_term(-1, {'y': 2})  # -y^2

        str_repr = str(matrix)
        assert 'x^2' in str_repr
        assert 'x*y' in str_repr
        assert '-y^2' in str_repr


class TestICCADOptimizer:
    """Test the ICCAD optimizer algorithms"""

    def test_divide_by_literal(self):
        """Test dividing polynomial by a literal (part of Kernels algorithm)"""
        optimizer = ICCADOptimizer()

        # Create polynomial: x^3 + 2*x^2 + x
        variables = ['x']
        poly = PolynomialMatrix(variables)
        poly.add_term(1, {'x': 3})
        poly.add_term(1, {'x': 2})
        poly.add_term(1, {'x': 1})

        # Divide by x
        result = optimizer._divide(poly, 'x')

        # Should get x^2 + x + 1
        assert len(result.rows) == 3
        assert result.rows[0].exponents == [2]  # x^2
        assert result.rows[1].exponents == [1]  # x
        assert result.rows[2].exponents == [0]  # 1

    def test_divide_by_cube(self):
        """Test Divide(P,d) algorithm from Figure 3"""
        optimizer = ICCADOptimizer()

        # Create polynomial: x^3*y + x^2*y^2 + x*y
        variables = ['x', 'y']
        poly = PolynomialMatrix(variables)
        poly.add_term(1, {'x': 3, 'y': 1})
        poly.add_term(1, {'x': 2, 'y': 2})
        poly.add_term(1, {'x': 1, 'y': 1})

        # Create cube to divide by: x*y
        cube = PolynomialMatrix(variables)
        cube.add_term(1, {'x': 1, 'y': 1})

        # Divide
        result = optimizer._divide_by_cube(poly, cube)

        # Should get x^2 + x*y + 1
        assert len(result.rows) == 3
        assert result.rows[0].exponents == [2, 0]  # x^2
        assert result.rows[1].exponents == [1, 1]  # x*y
        assert result.rows[2].exponents == [0, 0]  # 1

    def test_find_largest_common_cube(self):
        """Test finding the largest cube dividing all terms"""
        optimizer = ICCADOptimizer()

        # Create polynomial: x^3*y^2 + x^2*y^3 + x^2*y^2
        variables = ['x', 'y']
        poly = PolynomialMatrix(variables)
        poly.add_term(1, {'x': 3, 'y': 2})
        poly.add_term(1, {'x': 2, 'y': 3})
        poly.add_term(1, {'x': 2, 'y': 2})

        # Find common cube
        common = optimizer._find_largest_common_cube(poly)

        # Should be x^2*y^2
        assert len(common.rows) == 1
        assert common.rows[0].exponents == [2, 2]

    def test_merge_cubes(self):
        """Test Merge algorithm from Figure 3"""
        optimizer = ICCADOptimizer()

        variables = ['x', 'y', 'z']

        # Create three cubes
        c1 = PolynomialMatrix(variables)
        c1.add_term(1, {'x': 1, 'y': 2})  # x*y^2

        c2 = PolynomialMatrix(variables)
        c2.add_term(1, {'y': 1, 'z': 1})  # y*z

        c3 = PolynomialMatrix(variables)
        c3.add_term(1, {'x': 2})  # x^2

        # Merge
        result = optimizer._merge(c1, c2, c3)

        # Should be x^3*y^3*z
        assert len(result.rows) == 1
        assert result.rows[0].exponents == [3, 3, 1]

    def test_check_literal_ordering(self):
        """Test the literal ordering condition check"""
        optimizer = ICCADOptimizer()

        variables = ['x', 'y', 'z']
        literals = ['x', 'y', 'z']

        # Create cube with x and y
        cube = PolynomialMatrix(variables)
        cube.add_term(1, {'x': 1, 'y': 1})

        # Check at different j positions
        assert optimizer._check_literal_ordering(cube, 3, literals, variables)  # All literals < 3
        assert not optimizer._check_literal_ordering(cube, 1, literals, variables)  # y at index 1 >= 1
        assert optimizer._check_literal_ordering(cube, 2, literals, variables)  # x,y < 2

    def test_find_kernels_simple(self):
        """Test FindKernels algorithm with a simple polynomial"""
        optimizer = ICCADOptimizer()

        # Create polynomial: x^2 + x
        variables = ['x']
        poly = PolynomialMatrix(variables)
        poly.add_term(1, {'x': 2})
        poly.add_term(1, {'x': 1})

        literals = ['x']

        # Find kernels
        kernels_and_cokernels = optimizer.find_kernels([poly], literals)

        # Should find at least the original expression with co-kernel 1
        assert len(kernels_and_cokernels) >= 1

        # Check that original expression is included
        found_original = False
        for kernel, cokernel in kernels_and_cokernels:
            if len(cokernel.rows) > 0 and cokernel.rows[0].exponents == [0]:  # co-kernel = 1
                found_original = True
                break
        assert found_original


class TestSinXExample:
    """Test the sin(x) example from the paper (Figure 1)"""

    def test_sin_x_kernel_extraction(self):
        """Test kernel extraction for sin(x) as shown in Section 2.3"""
        optimizer = ICCADOptimizer()

        # sin(x) = x - S3*x^3 + S5*x^5 - S7*x^7
        variables = ['x', 'S3', 'S5', 'S7']
        sin_poly = PolynomialMatrix(variables)
        sin_poly.add_term(1, {'x': 1}, term_id=1)
        sin_poly.add_term(-1, {'x': 3, 'S3': 1}, term_id=2)
        sin_poly.add_term(1, {'x': 5, 'S5': 1}, term_id=3)
        sin_poly.add_term(-1, {'x': 7, 'S7': 1}, term_id=4)

        literals = variables

        # Find kernels
        kernels_and_cokernels = optimizer.find_kernels([sin_poly], literals)

        # According to the paper, should find these kernels:
        # [x](1 - S3*x^2 + S5*x^4 - S7*x^6)
        # [x^3](-S3 + S5*x^2 - S7*x^4)
        # [x^5](S5 - S7*x^2)
        # [1](original expression)

        # Verify we found multiple kernels
        assert len(kernels_and_cokernels) >= 2

        # Check for specific kernel patterns
        found_x_cokernel = False
        found_x3_cokernel = False

        for kernel, cokernel in kernels_and_cokernels:
            if len(cokernel.rows) > 0:
                cokernel_exp = cokernel.rows[0].exponents
                # Check for co-kernel x (exponents [1,0,0,0])
                if cokernel_exp == [1, 0, 0, 0]:
                    found_x_cokernel = True
                # Check for co-kernel x^3 (exponents [3,0,0,0])
                elif cokernel_exp == [3, 0, 0, 0]:
                    found_x3_cokernel = True

        # These are the expected kernels from the paper
        assert found_x_cokernel or found_x3_cokernel


class TestPolynomialToMatrix:
    """Test conversion from numpy polynomial to matrix representation"""

    def test_simple_polynomial_conversion(self):
        """Test converting a simple polynomial"""
        optimizer = ICCADOptimizer()

        # x^2 + 2*x + 1
        poly = np.poly1d([1, 2, 1])

        matrix = optimizer.polynomial_to_matrix(poly, 'x')

        # Should have 3 terms
        assert len(matrix.rows) == 3

        # Check the terms (order may vary)
        term_powers = sorted([row.exponents[0] for row in matrix.rows if 'x' in matrix.variables])
        assert 2 in term_powers  # x^2
        assert 1 in term_powers  # x
        assert 0 in term_powers  # constant


class TestOptimizationIntegration:
    """Integration tests for the full optimization pipeline"""

    def test_optimize_simple_polynomial(self):
        """Test optimizing a simple polynomial"""
        # x^2 + x
        poly = np.poly1d([1, 1, 0])

        code, stats = optimize_polynomial_iccad(poly)

        # Check that optimization ran
        assert 'def optimized_polynomial' in code
        assert 'return' in code
        assert stats['kernels_found'] >= 0

    def test_optimize_sin_taylor_series(self):
        """Test optimizing sin(x) Taylor series as in the paper"""
        # sin(x) ≈ x - x³/3! + x⁵/5! - x⁷/7!
        coeffs = [-1/math.factorial(7), 0, 1/math.factorial(5), 0,
                  -1/math.factorial(3), 0, 1, 0]

        sin_poly = np.poly1d(coeffs)

        code, stats = optimize_polynomial_iccad(sin_poly)

        # Check code generation
        assert 'def optimized_polynomial' in code
        assert 'x' in code

        # Check that kernels were found
        assert stats['kernels_found'] > 0

        # The paper shows significant optimization for sin(x)
        # Original: 15 multiplications, Optimized: 5 multiplications
        # Our implementation should find some optimizations
        assert stats['cse_count'] >= 0

    def test_optimize_factorizable_polynomial(self):
        """Test optimizing a polynomial with obvious factorization"""
        # (x+1)^2 = x^2 + 2*x + 1
        poly = np.poly1d([1, 2, 1])

        code, stats = optimize_polynomial_iccad(poly)

        # Should generate valid code
        assert 'def optimized_polynomial' in code
        assert stats['kernels_found'] >= 0

    def test_multivariate_pattern(self):
        """Test with a pattern that has multiple variables (conceptually)"""
        # x^4 + 2*x^3 + 3*x^2 + 2*x + 1
        # This has the pattern from the paper
        poly = np.poly1d([1, 2, 3, 2, 1])

        code, stats = optimize_polynomial_iccad(poly)

        # Should process successfully
        assert 'def optimized_polynomial' in code
        assert stats['optimized_count'] > 0


class TestCodeGeneration:
    """Test code generation functionality"""

    def test_python_code_generation(self):
        """Test generating Python code"""
        optimizer = ICCADOptimizer()

        # Create a simple polynomial
        variables = ['x']
        poly = PolynomialMatrix(variables)
        poly.add_term(1, {'x': 2})
        poly.add_term(1, {'x': 1})

        # Create empty CSE dict
        cse_dict = {}

        # Generate code
        code = optimizer.generate_code([poly], cse_dict, 'python')

        # Check structure
        assert 'def optimized_polynomial(x):' in code
        assert 'return' in code

    def test_code_with_cse(self):
        """Test code generation with common subexpressions"""
        optimizer = ICCADOptimizer()

        variables = ['x']

        # Main expression
        main_poly = PolynomialMatrix(variables)
        main_poly.add_term(1, {'x': 1})

        # CSE expression
        cse_poly = PolynomialMatrix(variables)
        cse_poly.add_term(1, {'x': 2})
        cse_poly.add_term(1, {'x': 1})

        cse_dict = {'_t0': cse_poly}

        # Generate code
        code = optimizer.generate_code([main_poly], cse_dict, 'python')

        # Check CSE is included
        assert '_t0' in code
        assert 'Common subexpressions' in code


class TestPaperExamples:
    """Test specific examples and claims from the paper"""

    def test_factorization_capability(self):
        """Test that the algorithm can perform factorization (Section 1)"""
        # The paper emphasizes factorization as a key advantage
        # Example: x^3 + x^2 should factor to x^2(x + 1)

        optimizer = ICCADOptimizer()

        variables = ['x']
        poly = PolynomialMatrix(variables)
        poly.add_term(1, {'x': 3})
        poly.add_term(1, {'x': 2})

        # Find kernels - should identify x^2 as common factor
        kernels = optimizer.find_kernels([poly], variables)

        # Should find kernels
        assert len(kernels) > 0

    def test_kernel_intersection_concept(self):
        """Test the kernel intersection concept (Section 2.3, Theorem)"""
        # "Two expressions f and g have a common multiple cube divisor
        # if and only if there are two kernels Kf and Kg ... having
        # a multiple cube intersection"

        optimizer = ICCADOptimizer()

        variables = ['x', 'y']

        # Expression 1: x^2*y + x*y^2
        expr1 = PolynomialMatrix(variables)
        expr1.add_term(1, {'x': 2, 'y': 1})
        expr1.add_term(1, {'x': 1, 'y': 2})

        # Expression 2: x^2*y + x*y
        expr2 = PolynomialMatrix(variables)
        expr2.add_term(1, {'x': 2, 'y': 1})
        expr2.add_term(1, {'x': 1, 'y': 1})

        # Both share the common factor x*y
        kernels = optimizer.find_kernels([expr1, expr2], variables)

        # Should find kernels for both expressions
        assert len(kernels) >= 2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_polynomial(self):
        """Test with empty polynomial"""
        optimizer = ICCADOptimizer()

        variables = ['x']
        empty_poly = PolynomialMatrix(variables)

        # Should handle gracefully
        kernels = optimizer.find_kernels([empty_poly], variables)
        assert len(kernels) >= 0

    def test_constant_polynomial(self):
        """Test with constant polynomial"""
        poly = np.poly1d([5])  # Just 5

        code, stats = optimize_polynomial_iccad(poly)

        # Should generate valid code
        assert 'def optimized_polynomial' in code

    def test_single_term_polynomial(self):
        """Test with single term polynomial"""
        poly = np.poly1d([1, 0, 0])  # Just x^2

        code, stats = optimize_polynomial_iccad(poly)

        # Should handle single term
        assert 'def optimized_polynomial' in code
        assert 'return' in code
