#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
import os
import csv
import subprocess as sp
from multiprocessing import cpu_count
import sys
import re
import logging
import pandas as ps
import yaml

if len(sys.argv) > 1:
    file = sys.argv[1]
    fileName = os.path.basename(file)
    parentDirectoryPath = os.path.dirname(file)
    vcfFilePath = file + '.vcf'
    ensemblFilePath = file + '.ensembl'
    logging.basicConfig(filename='{}.log'.format(file), filemode='a+', level=logging.DEBUG)
    logging.info(" Starting annotation pipleline ")

else:
    logging.info("Please pass the absolute path of the file to annotate")

def run():
    formatToVcfOrEnsemblAndSave()
    proccesVCF()
    #annotateFile(vcfFilePath)
    annotateFile(ensemblFilePath)
    #mergeResultsFiles(vcfFilePath, ensemblFilePath)
    logging.info("Annotating is complete")


def formatToVcfOrEnsemblAndSave():
    with open(file, 'r') as delimitedFile, \
            open(vcfFilePath, "w") as vcfFile, \
            open(ensemblFilePath, "w") as ensembl:
        reader = csv.DictReader(delimitedFile, delimiter="\t")
        logging.info("Writing {0} to VCF".format(file))
        vcfFile.write("#chrom\tpos\tid\tref\talt\tqual\tfilter\tinfo\n")
        ensembl.write("#chrom\tpos\tend\tref/alt\tstrand\tid\n")
        rowCount = 0
        for row in reader:
            if isRowValidForProcessing(row):
                rowCount += 1
                if rowIsEnsembl(row):
                    formatRowToEnsemblAndWrite(row, ensembl)
                else:
                    formatRowToVCFAndWrite(row, vcfFile)

        message = "The file {0} has {1} data points (including header)".format(file, (rowCount - 1))
        logging.info(message)

def rowIsEnsembl(row):
    refAllele = row["ref_allele"]
    altAllele = row["alt_allele"]
    return bool(re.search('-',refAllele)) or bool(re.search('-', altAllele))

def isRowValidForProcessing(row):
    isValid = True
    hg38RE = "(?i)(hg38|grch38|38)"
    if not bool(re.match(hg38RE, row["genome_assembly"])):
        logging.warning("Warning found legacy data : {0}".format(row.items()))
        isValid = False
    elif anyGenomicCoordinateAreMissing(row):
        logging.info(
            "Row has incomplete data : {0} in file {1} caused by missing chro,seq start, ref or alt allele data"
                .format(row.items(), vcfFilePath))
        isValid = False
    return isValid

def proccesVCF():
        logging.info("Sorting and removing duplicates in VCF")
        #sortInPlace(vcfFilePath)
        dropDuplicates(vcfFilePath)
        dropDuplicates(ensemblFilePath)

def dropDuplicates(vcfFilePath):
    vcfDf = ps.read_csv(vcfFilePath, sep='\t', keep_default_na=False, na_values=[''], dtype=str)
    vcfDf.drop_duplicates(inplace=True)
    vcfDf.to_csv(vcfFilePath, sep='\t', index=False, na_rep='')

def formatRowToVCFAndWrite(row, vcfFile):
    formattedChromo = formatChromo(row["chromosome"])
    posId = createPosId(row, row["seq_start_position"], row["seq_start_position"])
    vcfRow = "{0}\t{1}\t{2}\t{3}\t{4}\t.\t.\t.\n".format(formattedChromo, row["seq_start_position"], posId,
                                                           row["ref_allele"], row["alt_allele"])
    vcfFile.write(vcfRow)

def formatRowToEnsemblAndWrite(row, ensemblFile):
    formattedChromo = formatChromo(row["chromosome"])
    startPos,endPos = resolveEnsemblEndPos(row)
    posId = createPosId(row, startPos, endPos)
    ensemblRow = "{0}\t{1}\t{2}\t{3}/{4}\t+\t{5}\n".format(formattedChromo, startPos, endPos,
                                                           row["ref_allele"], row["alt_allele"], posId)
    ensemblFile.write(ensemblRow)

def resolveEnsemblEndPos(row):
    startPos = row['seq_start_position']
    endPos = startPos
    if bool(re.search("-", row["ref_allele"])):
        #insertion rule: Start - 1 = end coordinate
        endPos = int(startPos) - 1
    elif bool(re.search("-", row["alt_allele"])):
        #Deletion rule: Endpos = startPos + ( len(refAllele) - 1 )
        endPos = int(startPos ) + len(row["ref_allele"]) - 1
    return startPos, endPos

def createPosId(row, startPos, endPos):
    return "{}_{}-{}_{}_{}".format(formatChromo(row["chromosome"]), startPos, endPos,
                                row["ref_allele"], row["alt_allele"])

def anyGenomicCoordinateAreMissing(row):
    return not row["chromosome"] or not row["seq_start_position"] or not row["ref_allele"] or not row["alt_allele"]

def allGenomicDataIsMissing(row):
    return not row["chromosome"] and not row["seq_start_position"] and not row["ref_allele"] and not row["alt_allele"]

def formatChromo(givenChromo):
    incorrectChrFormat = "(?i)^([0-9]{1,2}|[xym]{1}|mt|un)$"
    isMatch = re.match(incorrectChrFormat, givenChromo)
    if isMatch:
        chromo = "chr" + isMatch.group(1)
    else:
        chromo = givenChromo
    return chromo

def annotateFile(vepIn):
    fastaDir, alleleDB, singularityVepImage, vepArgumentsList = getVepConfigurations()
    vepArguments = " ".join(vepArgumentsList)
    vepWarningFile = vepIn + ".vepWarnings"
    vepOut = vepIn + ".ANN"
    threads = cpu_count() * 2
    vepCMD = """vep {0} --fork={1} --warning_file {2} -cache -dir_cache {3} -fasta {4} -i {5} -o {6} 2>> {7}.log"""\
        .format(vepArguments, threads, vepWarningFile, alleleDB, fastaDir, vepIn, vepOut, file)
    logging.info("singularity exec {0} {1}".format(singularityVepImage, vepCMD))
    returnSignal = sp.call(
        "singularity exec {0} {1}".format(singularityVepImage, vepCMD), shell=True)
    if (returnSignal != 0):
        raise Exception("Vep returned a non-zero exit code {}".format(returnSignal))

def getVepConfigurations():
    with open('./config.yaml', 'r') as config:
        configDirs = yaml.safe_load(config)
        fastaDir = configDirs.get("fastaDir")
        alleleDB = configDirs.get("alleleDB")
        singularityVepImage = configDirs.get("vepSingularityImage")
        vepArguments = configDirs.get("vepArguments")
        if not os.path.exists(fastaDir):
            raise IOError("Fasta database does not exist at {}".format(fastaDir))
        if not os.path.exists(alleleDB):
            raise IOError("vep data base does not exist at {}".format(alleleDB))
        if not os.path.exists(singularityVepImage):
            raise IOError("singularity vep image does not exist at {}".format(singularityVepImage))
    return fastaDir,alleleDB,singularityVepImage,vepArguments


if len(sys.argv) > 1:
    run()
