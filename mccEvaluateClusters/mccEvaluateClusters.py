import os
import sys
import getopt
import subprocess

import PyXMCDA

from MccEval import *

from optparse import OptionParser

def main(argv=None):
    
    if argv is None:
        argv = sys.argv
        
    parser = OptionParser()

    parser.add_option("-i", "--in", dest="in_dir")
    parser.add_option("-o", "--out", dest="out_dir")

    (options, args) = parser.parse_args(argv[1:])

    in_dir = options.in_dir
    out_dir = options.out_dir

    # Creating a list for error messages
    errorList = []
    
    if not in_dir:
        errorList.append("option --in is missing")
    if not out_dir:
        errorList.append("option --out is missing")
    # Creating a list for log messages
    logList = []

    if not errorList:  
        if not os.path.isfile (in_dir+"/alternatives.xml"):
            errorList.append("alternatives.xml is missing")
        if not os.path.isfile (in_dir+"/preferenceRelation.xml"):
            errorList.append("preferenceRelation.xml is missing")
        if not os.path.isfile (in_dir+"/alternativesAffectations.xml"):
            errorList.append("alternativesAffectations.xml is missing")
        if not os.path.isfile (in_dir+"/clustersRelations.xml"):
            errorList.append("clustersRelations.xml is missing")

    if not errorList:
        # We parse all the mandatory input files
        xmltree_alternatives = PyXMCDA.parseValidate(in_dir+"/alternatives.xml")
        xmltree_preferenceRelation = PyXMCDA.parseValidate(in_dir+"/preferenceRelation.xml")
        xmltree_alternativesAffectations = PyXMCDA.parseValidate(in_dir+"/alternativesAffectations.xml")
        xmltree_clustersRelations = PyXMCDA.parseValidate(in_dir+"/clustersRelations.xml")
        
        # We check if all mandatory input files are valid
        if xmltree_alternatives == None :
            errorList.append("alternatives.xml can't be validated.")
        if xmltree_preferenceRelation == None :
            errorList.append("preferenceRelation.xml can't be validated.")
        if xmltree_alternativesAffectations == None :
            errorList.append("alternativesAffectations.xml can't be validated.")
        if xmltree_clustersRelations == None :
            errorList.append("clustersRelations.xml can't be validated.")
            
        if not errorList :

            alternativesId = PyXMCDA.getAlternativesID(xmltree_alternatives)
            alternativesRel = PyXMCDA.getAlternativesComparisonsValues(xmltree_preferenceRelation, alternativesId)
            
            if not alternativesId :
                errorList.append("No active alternatives found.")
            if not alternativesRel :
                errorList.append("Problems between relation and alternatives.")
            missing_eval = False
            for o in alternativesId:
                if not (o in alternativesRel):
                    missing_eval = True
                    break
                else:
                    for p in alternativesId:
                        if not (p in alternativesRel[o]):
                            missing_eval = True
                            break
                        else:
                            if not ('i' in alternativesRel[o][p]):
                                missing_eval = True
                                break
                            if not ('p+' in alternativesRel[o][p]):
                                missing_eval = True
                                break
                            if not ('p-' in alternativesRel[o][p]):
                                missing_eval = True
                                break
                            if not ('j' in alternativesRel[o][p]):
                                missing_eval = True
                                break
            if missing_eval:
                errorList.append("Not all alternatives from alternatives.xml contain evaluations in preferenceRelation.xml, or evaluations are incomplete. Possible inputs from different sources")
                
            alternativesAffectations = PyXMCDA.getAlternativesAffectations(xmltree_alternativesAffectations)
            Knames = []
            for o in alternativesId:
                clusterId = alternativesAffectations[o]
                if not (clusterId in Knames):
                    Knames.append(clusterId)
            
            if Knames == []:
                errorList.append("No clusters found.")
                
            K = {}
            for clusterId in Knames:
                K[clusterId] = []
            for o in alternativesId:
                K[alternativesAffectations[o]].append(o)
                
            clustersRel = PyXMCDA.getCategoriesComparisonsValues(xmltree_clustersRelations, Knames)
            
            if not clustersRel :
                errorList.append("Problems with clusters relations.")
                
            RK = {}
            for cid1 in Knames:
                RK[cid1] = {}
                for cid2 in Knames:
                    if cid1 == cid2:
                        RK[cid1][cid2] = 'i'
                    else:
                        RK[cid1][cid2] = ''
            missing_eval = False
            for cid1 in Knames:
                for cid2 in Knames:
                    if cid1 != cid2:
                        found = False
                        if cid1 in clustersRel:
                            if cid2 in clustersRel[cid1]:
                                found = True
                                RK[cid1][cid2] = clustersRel[cid1][cid2]
                                if clustersRel[cid1][cid2] == 'p+':
                                    RK[cid2][cid1] = 'p-'
                                elif clustersRel[cid1][cid2] == 'p-':
                                    RK[cid2][cid1] = 'p+'
                                else:
                                    RK[cid2][cid1] = clustersRel[cid1][cid2]
                        elif cid2 in clustersRel:
                            if cid1 in clustersRel[cid2]:
                                found = True
                                RK[cid2][cid1] = clustersRel[cid2][cid1]
                                if clustersRel[cid2][cid1] == 'p+':
                                    RK[cid1][cid2] = 'p-'
                                elif clustersRel[cid2][cid1] == 'p-':
                                    RK[cid1][cid2] = 'p+'
                                else:
                                    RK[cid1][cid2] = clustersRel[cid2][cid1]
                        if not found:
                            missing_eval = True
                            break
            if missing_eval:
                errorList.append("Incomplete clusters relations. Each pair needs an evaluation.")


        if not errorList :
            E = MccEval(alternativesId, alternativesRel, Knames, K, RK)
            o_nr,o_r,o_t,o_q = E.GetPerformances()
            
            logList.append("%.2f %% (%d/%d) relations in accordance to the Non-Relational Clustering problematic"%(200*o_nr/len(alternativesId)/(len(alternativesId) - 1),o_nr,len(alternativesId)*(len(alternativesId) - 1)/2))
            logList.append("%.2f %% (%d/%d) relations in accordance to the Relational Clustering problematic"%(200*o_r/len(alternativesId)/(len(alternativesId) - 1),o_r,len(alternativesId)*(len(alternativesId) - 1)/2))
            logList.append("%d cycles detected"%(o_t))
            logList.append("%d relations in discordance to the {p+,p-}-exclusivity property"%(o_q))                    
            
        # Creating log and error file, messages.xml
        fileMessages = open(out_dir+"/messages.xml", 'w')
        PyXMCDA.writeHeader (fileMessages)

        if not errorList :
            PyXMCDA.writeLogMessages (fileMessages, ["Execution ok"] + logList)
        else :
            PyXMCDA.writeErrorMessages (fileMessages, errorList)

        PyXMCDA.writeFooter(fileMessages)
        fileMessages.close()

if __name__ == "__main__":
    sys.exit(main())


            
