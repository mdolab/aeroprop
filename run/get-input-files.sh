#!/bin/bash

DIR=$(dirname $0)
wget -O $DIR/INPUT.tar.gz http://umich.edu/~mdolaboratory/aeroprop_files/INPUT.tar.gz
tar -xzf $DIR/INPUT.tar.gz -C $DIR/