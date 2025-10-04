#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "poly.h"


static inline double cse_Polynomial_Sin_Deg7(float x) {
  double xd = (double)x;
  double z = xd * xd;
  double t = fma(-1.9841269841269841e-4, z, 8.3333333333333332e-3);
  t = fma(t, z, -1.6666666666666666e-1);
  t = fma(t, z, 1.0);
  return xd * t;
}


static inline double cse_Polynomial_Sin_Deg9(float x) {
  double xd = (double)x;
  double z = xd * xd;
  double t = fma(2.7557319223985893e-06, z, -1.9841269841269841e-4);
  t = fma(t, z, 8.3333333333333332e-3);
  t = fma(t, z, -1.6666666666666666e-1);
  t = fma(t, z, 1.0);
  return xd * t;
}


static inline double cse_Polynomial_SqrtX1_Deg3(float x) {
  double xd = (double)x;
  double t = fma(6.25e-2, xd, -1.25e-1);
  t = fma(t, xd, 5.0e-1);
  t = fma(t, xd, 1.0);
  return t;
}


static inline double cse_Polynomial_Cos_Deg6(float x) {
  double xd = (double)x;
  double z = xd * xd;
  double t = fma(-1.3888888888888889e-3, z, 4.1666666666666664e-2);
  t = fma(t, z, -5.0e-1);
  t = fma(t, z, 1.0);
  return t;
}


static inline double cse_Polynomial_Cos_Deg12(float x) {
  double xd = (double)x;
  double z = xd * xd;
  double t = fma(2.08767569878681e-09, z, -2.7557319223985888e-07);
  t = fma(t, z, 2.4801587301587302e-05);
  t = fma(t, z, -1.3888888888888889e-03);
  t = fma(t, z, 4.1666666666666664e-02);
  t = fma(t, z, -5.0e-1);
  t = fma(t, z, 1.0);
  return t;
}


static inline double cse_Dyadic_Polynomial_Cos_Deg12(float x) {
  double xd = (double)x;
  double z = xd * xd;
  double t = fma(-2.0563602447509766e-05, z, -1.3113021850585938e-06);
  t = fma(t, z, 2.3901462554931641e-05);
  t = fma(t, z, -0.0013893246650695801);
  t = fma(t, z, 0.041666388511657715);
  t = fma(t, z, -0.50000017881393433);
  t = fma(t, z, 0.99999988079071045);
  return t;
}


// For ctypes/cffi usage.
double poly_sin_deg7(float x) { return cse_Polynomial_Sin_Deg7(x); }
double poly_sin_deg9(float x) { return cse_Polynomial_Sin_Deg9(x); }
double poly_sqrtx1_deg3(float x) { return cse_Polynomial_SqrtX1_Deg3(x); }
double poly_cos_deg6(float x) { return cse_Polynomial_Cos_Deg6(x); }
double poly_cos_deg12(float x) { return cse_Polynomial_Cos_Deg12(x); }
double dyadic_poly_cos_deg12(float x) { return cse_Dyadic_Polynomial_Cos_Deg12(x); }
