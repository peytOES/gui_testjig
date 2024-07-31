#!/bin/bash

VERSION=`git describe --tags`

echo $VERSION
git archive -v --prefix=$VERSION/ -o $VERSION.zip  HEAD
