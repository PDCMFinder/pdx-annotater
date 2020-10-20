#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import os
import csv
import subprocess as sp
import sys
import re
import logging
from utilities import vcfUtilities

if len(sys.argv) > 1:
    file = sys.argv[1]
    fileName = os.path.basename(file)
    parentDirectoryPath = os.path.dirname(file)
    provider = os.path.dirname(parentDirectoryPath)
    Updog = os.path.dirname(provider)
    ensemblFilePath = file + '.vcf'
    logging.basicConfig(filename='{}.log'.format(file), filemode='a+', level=logging.DEBUG)
    logging.info(" Starting annotation pipleline ")

else:
    logging.info("Please pass the absolute path of the file to annotate")

def run():
    #formatToVCFAndSave(file)
    formatToEnsemblAndSave(file)
    proccesVCF()
    annotateVCF(ensemblFilePath, file)
    logging.info("Annotating is complete")


def formatToVCFAndSave(filePath):
    with open(filePath) as delimitedFile, \
            open(ensemblFilePath, "w+") as vcfFile:
        chmodFile(ensemblFilePath)
        reader = getDelimitedFileReader(delimitedFile, filePath)
        logging.info("Writing {0} to VCF".format(filePath))
        vcfFile.write("#chrom\tpos\tid\tref\talt\tqual\tfilter\tinfo\n")
        rowCount = 0
        try:
            for row in reader:
                rowCount += 1
                proccessRowToVCF(row, vcfFile)
        except EOFError:
            logging.info("End of file at {}".format(rowCount))
        message = "The file {0} has {1} data points (including header)".format(filePath, rowCount)
        logging.info(message)

def formatToEnsemblAndSave(filePath):
    hg38RE = "(?i)(hg38|grch38|38)"
    with open(filePath) as delimitedFile, \
            open(ensemblFilePath, "w+") as ensemblFile:
        chmodFile(ensemblFilePath)
        reader = getDelimitedFileReader(delimitedFile, filePath)
        logging.info("Writing {0} to Ensembl format".format(filePath))
        rowCount = 0
        try:
            for row in reader:
                rowCount += 1
                if not bool(re.match(hg38RE, row["genome_assembly"])):
                    logging.warning("Warning found legacy data : {0}".format(row.items()))
                else:
                    formattedChromo = vcfUtilities.formatChromo(row["chromosome"])
                    posId = createPosId(row)
                    vcfRow = "{0}\t{1}\t{2}\t{3}/{4}\t+\t{5}\n"\
                        .format(formattedChromo, row["seq_start_position"],row["seq_start_position"],row["ref_allele"], row["alt_allele"], posId)
                    ensemblFile.write(vcfRow)
        except EOFError:
            logging.info("End of file at {}".format(rowCount))
        message = "The file {0} has {1} data points (including header)".format(filePath, rowCount)
        logging.info(message)


def getDelimitedFileReader(delimitedFile, filePath):
    if filePath.endswith(".csv"):
        reader = csv.DictReader(delimitedFile, delimiter=",")
    else:
        reader = csv.DictReader(delimitedFile, delimiter="\t")
        if not filePath.endswith(".tsv"):
            logging.info("File {}  is not suffixed as tsv... procceding anyways".format(filePath))
    return reader

def proccessRowToVCF(row, vcfFile):
    hg38RE = "(?i)(hg38|grch38|38)"
    if not bool(re.match(hg38RE, row["genome_assembly"])):
        logging.warning("Warning found legacy data : {0}".format(row.items()))
    elif (anyGenomicCoordinateAreMissing(row)):
        logging.info(
            "Row has incomplete data : {0} in file {1} caused by missing chro,seq start, ref or alt allele data"
                .format(row.items(), ensemblFilePath))
    elif allGenomicDataIsMissing(row):
        raise EOFError
    else:
        formatRowToVCFAndWrite(row, vcfFile)

def proccesVCF():
        logging.info("Sorting and removing duplicates in VCF")
        vcfUtilities.sortInPlace(ensemblFilePath)
        vcfUtilities.dropDuplicates(ensemblFilePath)

def formatRowToVCFAndWrite(row, vcfFile):
    formattedChromo =  vcfUtilities.formatChromo(row["chromosome"])
    alleles = formatImproperInsertionsAndDeletions(row["ref_allele"], row["alt_allele"])
    posId = createPosId(row)
    vcfRow = "{0}\t{1}\t{2}\t{3}\t{4}\t.\t.\t.\n".format(formattedChromo, row["seq_start_position"], posId,
                                                           alleles[0], alleles[1])
    vcfFile.write(vcfRow)

def formatImproperInsertionsAndDeletions(refAllele, altAllele):
    if refAllele[0] == "-":
        formatedRefAllele = "N"
        formatedAltAllele = "N{}".format(altAllele)
    elif '-' in altAllele:
        logging.info("Ref allele {} not supported".format(refAllele))
    else:
        formatedRefAllele = refAllele
        formatedAltAllele = altAllele
    return [formatedRefAllele, formatedAltAllele]

def chmodFile(annoFilename):
        os.chmod(annoFilename, 0o666)

def createPosId(row):
    return "{}_{}_{}_{}".format(vcfUtilities.formatChromo(vcfUtilities.formatChromo(row["chromosome"])), row["seq_start_position"], row["ref_allele"], row["alt_allele"])


def anyGenomicCoordinateAreMissing(row):
    return not row["chromosome"] or not row["seq_start_position"] or not row["ref_allele"] or not row["alt_allele"]


def allGenomicDataIsMissing(row):
    return not row["chromosome"] and not row["seq_start_position"] and not row["ref_allele"] and not row["alt_allele"]


def annotateVCF(vcfFile, targetFile):
    workingDir = os.getcwd()
    fastaDir = workingDir + "/vepDBs/homo_sapiens/Homo_sapiens.GRCh38.dna.primary_assembly.fa"
    alleleDB = workingDir + "/vepDBs/homo_sapiens_vep_98_GRCh38"
    singularityVepImage = workingDir + "/pdx-liftover-vep_release98.3.simg"

    if not os.path.exists(fastaDir):
        raise IOError("Fasta database does not exist at {}".format(fastaDir))
    if not os.path.exists(alleleDB):
        raise IOError("vep data base does not exist at {}".format(alleleDB))
    if not os.path.exists(singularityVepImage):
        raise IOError("singularity vep image does not exist at {}".format(singularityVepImage))

    print(os.getcwd())

    vepIn = vcfFile
    vepWarningFile = targetFile + ".vepWarnings"
    vepOut = targetFile + ".ANN"

    vepCMD = """vep -e -q -check_existing --check_ref -symbol -polyphen -sift -merged -use_transcript_ref —hgvs —hgvsg —variant_class \
    -canonical -fork 4 -format ensembl -force -offline -no_stats --warning_file {0}  \
     -cache -dir_cache {1} -fasta {2} -i {3} -o {4} 2>> {5}.log""".format(vepWarningFile, alleleDB, fastaDir, vepIn,
                                                                          vepOut, file)

    logging.info("singularity exec {0} {1}".format(singularityVepImage, vepCMD))
    returnSignal = sp.call(
        "singularity exec {0} {1}".format(singularityVepImage, vepCMD), shell=True)
    if (returnSignal != 0):
        raise Exception("Vep returned a non-zero exit code {}".format(returnSignal))


if len(sys.argv) > 1:
    run()
