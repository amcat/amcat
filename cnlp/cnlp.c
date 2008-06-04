#include <Python.h>
#include <stdio.h>
#define _GNU_SOURCE 1
#include <string.h>
#define _GNU_SOURCE 1
#include <search.h>
#include <fcntl.h>
#include "stem.h"

// Preliminaries

typedef struct hsearch_data HS_DATA;

static PyObject* cnlp_initcount(PyObject*, PyObject*);
static PyObject* cnlp_count(PyObject*, PyObject*);
static PyObject* cnlp_tokenize(PyObject*, PyObject*);
static PyObject* cnlp_lemmatize(PyObject*, PyObject*);
static PyObject* cnlp_initlem(PyObject*, PyObject*);
static PyObject* cnlp_wplToWc(PyObject*, PyObject*);


static PyMethodDef CNLPMethods[] = {
    {"lemmatize",  cnlp_lemmatize, METH_VARARGS, "Lemmatizes a string."},
    {"initlem",  cnlp_initlem, METH_VARARGS, "Initializes the hash for lemmatizing with a list of word/P, lemma pairs."},
    {"tokenize",  cnlp_tokenize, METH_VARARGS, "Tokenizes a string."},
    {"wplToWc",  cnlp_wplToWc, METH_VARARGS, "Convert word/pos/lemma in lemma/Cat."},
    {"count",  cnlp_count, METH_VARARGS, "Count a number of words."},
    {"initcount", cnlp_initcount, METH_VARARGS, "Initialize the hash for counting with a list of string, int pairs"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC initcnlp(void)
{
  (void) Py_InitModule("cnlp", CNLPMethods);
}

// Helper methods


static int checkSequence(PyObject* s, char* what) {
  if (!PySequence_Check(s)) {
    char error[100]; sprintf(error, "%s is not a sequence", what);
    PyErr_SetString(PyExc_ValueError, error);
    return 0;
  }
  return 1;
}

static int checkSequenceN(PyObject* s, char* what, int n) {
  if (checkSequence(s, what) == 0) return 0;
  if (PySequence_Size(s) != n) {
    char error[100]; sprintf(error, "%s length is %i, expected: %i", what, PySequence_Size(s), n);
    PyErr_SetString(PyExc_ValueError, error);
    return 0;
  }
  return 1;
}

////////////////  LEMMATIZING /////////////////////

static PyObject* cnlp_initlem(PyObject *self, PyObject *args)
{
  PyObject* entries;
  if (!PyArg_ParseTuple(args, "O", &entries))
    return NULL;

  if (checkSequence(entries, "First argument") == 0) return NULL;

  int n = PySequence_Size(entries);
 
  HS_DATA *hashdata = (HS_DATA *) calloc(1, sizeof(HS_DATA));
  if (!hashdata) {
    PyErr_SetString(PyExc_Exception, "Cannot malloc hashdata!");
    return NULL;
    }

  //printf("size(int)=%i, sizeof(long)=%i, sizeof(void*)=%i", sizeof(int), sizeof(long), sizeof(void*));
  //printf("Initializing with %i entries, setting hash size to %i\n", n, n*3/2);

  if (!hcreate_r(n*3/2, hashdata)) {
    PyErr_SetString(PyExc_Exception, "Cannot initialize hash!");
    return NULL;
  }

  int i;
  PyObject* entry;
  for (i=0; i<n; i++) {
    entry = PySequence_GetItem(entries, i);
    if (checkSequence(entry, "entry") == 0) return NULL;
    if (checkSequenceN(entry, "entry", 2) == 0) return NULL;
    ENTRY item;
    item.key = PyString_AsString(PySequence_GetItem(entry, 0));
    item.data = PyString_AsString(PySequence_GetItem(entry, 1));
    //printf("Adding '%s' : '%s'\n", item.key, (char*) item.data);
    if (item.key == NULL || item.data == NULL) return NULL;
    ENTRY* dummy = NULL;
    if (!hsearch_r(item, ENTER, &dummy, hashdata)) {
      printf("Error, errno: %i, %i, %i, %i", errno, ENOMEM, hashdata->filled, hashdata->size);
      PyErr_SetString(PyExc_Exception, "Could not enter hash value!");
      return NULL;
    }
  }

  return Py_BuildValue("i", hashdata);//Py_RETURN_NONE;
}

static char* lemmatize(char* word, HS_DATA* hash) 
{
  ENTRY key;
  key.key = word;
  ENTRY* result;
  if (hsearch_r(key, FIND, &result, hash)) 
    return (*result).data;

  //printf("Could not find %s, using Porter\n", word);
  // split on slash, take left hand side
  char* w2;
  char* sep = strchr(word, '/');
  if (sep == NULL) {
    w2 = strdup(word);
  } else {
    int l = sep - word;
    w2 = strndup(word, l);
    if (!(sep[1] == 'A' || sep[1] == 'N' || sep[1] == 'V'))
      return w2;
  }
  
  if (w2 == NULL) {
      PyErr_SetString(PyExc_Exception, "Cannot copy String - str(n)dup returned NULL");
      return NULL;
    }
  //printf("Calling porter stemmer on %s\n", w2);
  Stem(w2);
  return w2;
}


static PyObject* cnlp_lemmatize(PyObject *self, PyObject *args)
{
  char *word;
  int hashpointer;
  if (!PyArg_ParseTuple(args, "si", &word, &hashpointer))
    return NULL;

  char* lemma = lemmatize(word, (HS_DATA*) hashpointer);

  if (lemma == NULL) 
    if (PyErr_Occurred) return NULL;
    else Py_RETURN_NONE;
  else
    return Py_BuildValue("s", lemma);
}


////////////////  COUNTING   //////////////////////

static PyObject* cnlp_initcount(PyObject *self, PyObject *args)
{
  PyObject* entries;
  if (!PyArg_ParseTuple(args, "O", &entries))
    return NULL;

  if (checkSequence(entries, "First argument") == 0) return NULL;

  int n = PySequence_Size(entries);
 
  HS_DATA *hashdata = (HS_DATA *) calloc(1, sizeof(HS_DATA));
  if (!hashdata) {
    PyErr_SetString(PyExc_Exception, "Cannot malloc hashdata!");
    return NULL;
    }

  //printf("Initializing with %i entries, setting hash size to %i\n", n, n*3/2);

  if (!hcreate_r(n*3/2, hashdata)) {
    PyErr_SetString(PyExc_Exception, "Cannot initialize hash!");
    return NULL;
  }

  int i;
  PyObject* entry;
  for (i=0; i<n; i++) {
    entry = PySequence_GetItem(entries, i);
    if (checkSequence(entry, "entry") == 0) return NULL;
    if (checkSequenceN(entry, "entry", 2) == 0) return NULL;
    ENTRY item;
    // use FAST_GET since we don't want a reference and we checked the bounds and nullity
    item.key = PyString_AsString(PySequence_Fast_GET_ITEM(entry, 0));
    item.data = (void*) PyInt_AsLong(PySequence_Fast_GET_ITEM(entry, 1));
    //printf("Adding '%s' : '%s'\n", item.key, (char*) item.data);
    if (item.key == NULL) {
      char error[100]; sprintf(error, "Keys cannot be None");
      PyErr_SetString(PyExc_ValueError, error);      
      return NULL;
    }
    
    ENTRY* dummy = NULL;
    if (!hsearch_r(item, ENTER, &dummy, hashdata)) {
      printf("Error, errno: %i, %i, %i, %i", errno, ENOMEM, hashdata->filled, hashdata->size);
      PyErr_SetString(PyExc_Exception, "Could not enter hash value!");
      return NULL;
    }
    Py_DECREF(entry); // since PySequence_GetItem gives a new referencs
  }
  //return Py_BuildValue("i", 1);
  return Py_BuildValue("i", hashdata);
}


// wplToWc(char* wpc)
//    Transforms a word/pos/lemma string to a lemma/category string. Categories are:
//    A (Adjective or Adverb), N (Noun), X (Auxilliary verbs), V (other verbs),
//    R (aRticles), M (Numbers), P (Prep), O (Pronoun), C (Conj), I (Int), U (Punct),
//    E (Proper Noun ('E'igennaam)
//    If parsing fails, returns NULL

static char* wplToWc(char* wpl) {
  char *pos, *lemma, *result, cat;
 
  pos = strchr(wpl, '/');
  if (!pos++) {printf("Could not find '/' in %s\n", wpl); return NULL;}

  lemma = strchr(pos, '/');
  if (!lemma++) {printf("Could not find second '/' in %s\n", wpl); return NULL;}
  
  if (!strncmp(pos, "V(hulp", 6)) cat = 'X';
  else if (!strncmp(pos, "N(eigen", 7)) cat = 'E';
  else if (!strncmp(pos, "Adj", 3)) cat = 'J';
  else if (!strncmp(pos, "Art", 3)) cat = 'R';
  else if (!strncmp(pos, "Num", 3)) cat = 'M';
  else if (!strncmp(pos, "Pron", 4)) cat = 'O';
  else if (!strncmp(pos, "Punc", 4)) cat = 'U';
  else cat = pos[0];

  result = calloc(strlen(lemma) + 3, sizeof(char)); // need lemma plus slash, cat, null character
  if (!result) {printf("Could not malloc result for wplToWc"); return NULL;}

  strcpy(result, lemma);
  result[strlen(lemma)] = '/';
  result[strlen(lemma) + 1] = cat;
  result[strlen(lemma) + 2] = '\0';
  return result;
}


static char* wplToW(char* wpl) {
  char *pos;
 
  pos = strchr(wpl, '/');
  if (!pos++) {printf("Could not find '/' in %s\n", wpl); return NULL;}

  return strndup(wpl, pos - wpl - 1);
}


static char* wplToL(char* wpl) {
  char *pos, *lemma;

  pos = strchr(wpl, '/');
  if (!pos++) {printf("Could not find '/' in %s\n", wpl); return NULL;}

  lemma = strchr(pos, '/');
  if (!lemma++) {printf("Could not find second '/' in %s\n", wpl); return NULL;}

  return strdup(lemma);
}


static PyObject* cnlp_wplToWc(PyObject *self, PyObject *args) {
  char *wpl, *wc;
  if (!PyArg_ParseTuple(args, "s", &wpl))
    return NULL;

  wc = wplToWc(wpl);

  if (!wc) Py_RETURN_NONE;
  return Py_BuildValue("s", wc);
}

static PyObject* cnlp_count(PyObject *self, PyObject *args)
{ 
  //  cnlp_count(text, hash_ptr, duplicate, lowercase, lemma)
  //     counts a set of words in a text
  //  @param text      a python string containing the text to be word-counted
  //  @param hash_ptr  a pointer obtained from initcount to the word dictionary
  //  @param duplicate boolean; if false this will modify up the input text. 
  //                   Only set this to be false if you have the only reference to
  //                   'text' and will not use it afterwards as this violates string
  //                   string immutability
  //  @param lowercase convert text to lowercase if true
  //  @param lemma     lemma options:
  //                   0 - count words 'as is'
  //                   1 - convert word/pos/lemma tokens to lemmaP tokens
  //                   2 - convert word/pos/lemma tokens to lemma tokens
  //                   3 - convert word/pos/lemma tokens to word tokens
  //  @return          a python dictionary {id: frequency} (id from worddict values)
  //     
  char *text, *word;
  int hashpointer, duplicate, lower, lemmap;
  int i;
  if (!PyArg_ParseTuple(args, "siiii", &text, &hashpointer, &duplicate, &lower, &lemmap))
    return NULL;
  HS_DATA* hash = (HS_DATA*) hashpointer;  
  
  char* (*conversion)(char*);
  switch (lemmap) {
  case 0: conversion = NULL; break;
  case 1: conversion = wplToWc; break;
  case 2: conversion = wplToL; break;
  case 3: conversion = wplToW; break;
  default:
      PyErr_SetString(PyExc_Exception, "Unknown lemmap option!");
      return NULL;
  }

  

  if (duplicate && lower) {
    char *text2 = malloc(strlen(text) * sizeof(char) + 1);
    for( i = 0; text[ i ]; i++)
      text2[ i ] = tolower( text[ i ] );
    text2[i] = '\0';
    text = text2;
  }
  else 
    if (duplicate) text = strdup(text);
    else if (lower) 
      for( i = 0; text[ i ]; i++)
	text[ i ] = tolower( text[ i ] );
	
  PyObject *dict = PyDict_New();
  
  //printf("starting count\n");
  for (word = strtok(text, " \n"); word != NULL; word = strtok(NULL, " \n")) {
    ENTRY key, *result;

    //printf("word: %s\n", word);
    if (conversion) word = conversion(word);
    if (word == NULL) {
	//printf("Parse problem, skipping!\n");
	continue;
    }
    
    key.key = word;
    if (!hsearch_r(key, FIND, &result, hash)) {
      //printf("Not found\n");
      continue;
    }
 
    if (lemmap) free(key.key);
 
    int wn = (int) result->data;
    PyObject* wordno = PyInt_FromLong(wn); // new ref
    //printf("%s -> %i\n", word, wn);
    PyObject* value = PyDict_GetItem(dict, wordno); // borrowed ref
    int newval = value == NULL ? 1 : PyInt_AsLong(value) + 1;
    PyObject* newvalue = PyInt_FromLong(newval); // new ref
    //printf("Setting %i to %i\n", val, newval);
    PyDict_SetItem(dict, wordno, newvalue);
    Py_DECREF(wordno);
    Py_DECREF(newvalue);
  }
  

  if (duplicate) free(text);
  //Py_DECREF(dict); // return as new reference
  return dict;
}

///////////// TOKENIZING //////////////////

#define is_ALPHA(c) (c >= 'A' && c <= 'Z') 
#define is_alpha(c) (c >= 'a' && c <= 'z')
#define is_Alpha(c) (is_ALPHA(c) || is_alpha(c))
#define is_digit(c) (c >= '0' && c <= '9')
#define is_alphanum(c)  (is_Alpha(c) || is_digit(c))
#define is_d(c) (c == 'D' || c == 'd')
#define is_m(c) (c == 'M' || c == 'm')
#define is_i(c) (c == 'I' || c == 'i')
#define is_p(c) (c == 'P' || c == 'p')


static PyObject* cnlp_tokenize(PyObject *self, PyObject *args)
{
  char *old, *new;
  int i;
  if (!PyArg_ParseTuple(args, "s", &old))
    return NULL;
  
  int size = strlen(old) * 3 / 2;
  new = malloc(size * sizeof(char));
  if (!new) {
    PyErr_SetString(PyExc_Exception, "Could not malloc!");
    return NULL;
  }
  
  int j=0;
  for(i=0; old[ i ]; i++) {
    if (j > (size-10)) {
      size = size * 3 / 2 ;
      //printf("Reallocing to %i", size);
      new = realloc(new, size * sizeof(char));
      if (!new) {
	PyErr_SetString(PyExc_Exception, "Could not realloc!");
	return NULL;
      }
    }
    // if char is_ not a word, and preceding is not a space, insert a space
    char o = old[i];
    //printf("%c : %i\n", o, isword);

    int isword = is_alphanum(o) || o==' '
      // keep decimal and thousand separators
      || ((o=='.' || o==',') && i>0 && is_digit(old[i-1]) && is_digit(old[i+1]))
      // keep period in abbreviations
      || (o=='.' && i>0 && is_Alpha(old[i-1]) && is_Alpha(old[i+1]))
      // keep periods ending an abbreviation (assuming next letter is not capitalized)
      || (o=='.' && i>0 && old[i+1] && old[i+2] && is_Alpha(old[i-1]) && old[i+1] == ' ' && is_alpha(old[i+2]))
      // keep periods after an initial (disregarding silly Th. style initials for the moment)
      || (o=='.' && i>1 && is_Alpha(old[i-1]) && !is_alphanum(old[i-2]))
      // keep periods after titles, currently Dhr, dr, mr, ir, ing, drs, prof, and mw 
      || (o=='.' && i>4 && (!is_alphanum(old[i-5]) && is_p(old[i-4]) && old[i-3]=='r' && old[i-2]=='o' && old[i-1]=='f'))
      || (o=='.' && i>3 && (!is_alphanum(old[i-4]) && is_d(old[i-3]) && old[i-2]=='h' && old[i-1]=='r'))
      || (o=='.' && i>3 && (!is_alphanum(old[i-4]) && is_d(old[i-3]) && old[i-2]=='r' && old[i-1]=='s'))
      || (o=='.' && i>2 && (!is_alphanum(old[i-3]) && is_d(old[i-2]) && old[i-1]=='r'))
      || (o=='.' && i>2 && (!is_alphanum(old[i-3]) && is_i(old[i-2]) && old[i-1]=='r'))
      || (o=='.' && i>3 && (!is_alphanum(old[i-4]) && is_i(old[i-3]) && old[i-2]=='n' && old[i-1]=='g'))
      || (o=='.' && i>2 && (!is_alphanum(old[i-3]) && is_m(old[i-2]) && old[i-1]=='w'))
      || (o=='.' && i>2 && (!is_alphanum(old[i-3]) && is_m(old[i-2]) && old[i-1]=='r'))
      // keep dashes between words
      || (o=='-' && i>1 && is_alphanum(old[i-1]) && is_alphanum(old[i-2]))
      // keep apostrophes in z'n, d'r etc between words
      || (o=='\'' && i>0 && old[i-1]=='z' && old[i+1]=='n')
      ;

    if (!isword && j>0 && new[j-1] != ' ' && !(new[j-1]=='\n' && old[i]=='\n')) new[j++] = ' ';
    new[ j++ ] = old[ i ];
    if (!isword && old[i+1] && old[i+1] != ' ' && !(old[i+1]=='\n' && old[i]=='\n')) new[j++] = ' ';
  }
  new[j] = '\0';
  
  PyObject* result = PyString_FromString(new);

  return result;
}

