#ifndef POLY_H
#define POLY_H

#ifdef __cplusplus
extern "C" {
#endif

// Exported API for polynomial evaluators
// All functions take float input and return double for precision

double poly_sin_deg7(float x);
double poly_sin_deg9(float x);
double poly_sqrtx1_deg3(float x);
double poly_cos_deg6(float x);
double poly_cos_deg12(float x);
double dyadic_poly_cos_deg12(float x);

#ifdef __cplusplus
}
#endif

#endif // POLY_H
