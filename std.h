#pragma once

#include <stdbool.h>

typedef struct {
    char* chars;
} str;

str str_new(char* chars);
str str_copy(str string);
bool str_eq(str string_a, str string_b);

str usr_tail(str string);
str usr_head(str string);
str usr_cat(str string_a, str string_b);
str usr_eq(str string_a, str string_b);
str usr_print(str string);
