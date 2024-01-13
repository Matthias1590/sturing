#include "std.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

str str_new(char* chars) {
    return (str) {
        .chars = chars
    };
}

str str_copy(str string) {
    size_t size = sizeof(char) * (strlen(string.chars) + 1);

    char* chars = malloc(size);
    memcpy(chars, string.chars, size);

    return str_new(chars);
}

bool str_eq(str string_a, str string_b) {
    return strcmp(string_a.chars, string_b.chars) == 0;
}

str usr_tail(str string) {
    if (*string.chars == '\0') {
        return string;
    }

    return str_new(string.chars + 1);
}

str usr_head(str string) {
    if (*string.chars == '\0') {
        return string;
    }

    string = str_copy(string);
    string.chars[strlen(string.chars) - 1] = '\0';

    return string;
}

str usr_cat(str string_a, str string_b) {
    size_t a_len = strlen(string_a.chars);
    size_t b_len = strlen(string_b.chars);

    char* chars = malloc(a_len + b_len + 1);
    memcpy(chars, string_a.chars, a_len);
    memcpy(chars + a_len, string_b.chars, b_len + 1);

    return str_new(chars);
}

str usr_eq(str string_a, str string_b) {
    return str_eq(string_a, string_b)
        ? str_new("true")
        : str_new("false");
}

str usr_print(str string) {
    printf("%s", string.chars);

    return str_new("");
}
