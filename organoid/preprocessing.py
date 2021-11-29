from typing import final
import matplotlib.pyplot as plt
import numpy as np
import os
from collections import Counter
import re

class Alignment:
    _closedWindows = 0
    # color pattern to be used
    colors = ['m','g','b','y','r']
    
    _colorVec = []
    _index = 0

    def __init__(self, saveDir):
        self.saveDir = saveDir

    def _numOrgs(self, initCoords):
        #  return counts of unique y values in sorted order

        y = initCoords[:,1]
        OrgsCnts = Counter(y)
        # list of tuples of key and value: y value and associated count
        yValCnts = OrgsCnts.items()
        yValCntsSorted = sorted(yValCnts)
        return np.array(yValCntsSorted)[:,1]

    def _initColors(self, initCoords, finalCoords, yValCnts):
        initGrpd, colors = self._groupAndColor(initCoords, yValCnts)
        finalGrpd, finalColors = self._groupAndColor(finalCoords, yValCnts)
        assert(colors == finalColors)
        return initGrpd, finalGrpd, colors
    
    def _groupAndColor(self, coords, yValCnts):
        # group coordinates by y values, sort x values within groups, assign colors to groups
        coordsYsort = sorted(coords, key = lambda column: column[1])

        patternDict = {}
        colors_used = [0,0,0,0,0,0]

        nColors = len(self.colors)
        start = 0

        for ix, cnt in enumerate(yValCnts):
            cnt = int(cnt)
            colIx = ix % nColors
            vals = np.array(coordsYsort[start:start+cnt])
            valsXsort = sorted(vals, key = lambda x: x[0])
            currColor = self.colors[colIx]
            currColor = self.colors[colIx]

            if currColor not in patternDict:
                patternDict[currColor] = valsXsort
            else:
                keyNum = colors_used[colIx]
                newKeyNum = keyNum + 1
                keyName = currColor + str(newKeyNum)
                patternDict[keyName] = valsXsort
                colors_used[colIx] = newKeyNum

            start = start + cnt

        return self._colorDict2Arr(patternDict)

    def _colorDict2Arr(self, colsDict):
        keys = list(colsDict.keys())
        coordList = []
        colList = []
        for key in keys:
            col = re.sub(r'[0-9]+', '', key)
            colList.extend([col for _ in range(len(colsDict[key]))])
            coordList.append(np.array(colsDict[key]))
        return np.vstack(coordList), colList

    def _fixColors(self, initCoords, finalCoords, colors):
        # Manually annotate to align color coding of two input patterns
        X = finalCoords[:,0]
        Y = finalCoords[:,1]
        xyVec = np.array([X,Y]).T
        numCoords = len(X)
        self._colorVec = colors.copy()

        refFig = plt.figure(1)
        plt.scatter(initCoords[:,0], initCoords[:,1], c = colors)
        plt.title("REFERENCE IMAGE")

        figColor = plt.figure(2, figsize=(8,8))
        for i, (x,y) in enumerate(zip(X,Y)):
            plt.scatter(x, y, c = colors[i], picker=5)

        def onclick(event):
            # get click location
            xclick = np.round(event.mouseevent.xdata,3)
            yclick = np.round(event.mouseevent.ydata, 3)
            clickCoord = np.array((xclick, yclick))
            print(xclick, yclick)

            print('Color mod options: magenta/green/blue/yellow/red')
            val = input("Enter value m/g/b/y/r: ")

            # record changes 
            clickVec = np.tile(clickCoord, (numCoords, 1))
            diff = clickVec - xyVec
            sumSqDiff = np.sum(diff*diff, axis=1)
            ix = np.argmin(sumSqDiff)
            self._index = ix
            print("Current Color is {}.".format(self._colorVec[ix]))
            self._colorVec[ix] = val
            print("New Color is {}.".format(self._colorVec[ix]))

            # redraw with changes
            event.artist.set_color(val)
            figColor.canvas.draw()
            
        def on_close(event):
            figNum = event.canvas.figure.number
            print("Figures {} has been closed.".format(figNum))
            self._closedWindows += 1

        cid = figColor.canvas.mpl_connect('pick_event', onclick)
        refFig.canvas.mpl_connect('close_event', on_close)
        figColor.canvas.mpl_connect('close_event', on_close)
        
        plt.axis('off')
        plt.show()

        # if both windows close, end return annotation
        if self._closedWindows == 2:
            print("### Exiting manual annotation ###")
            print()
            return self._colorVec
    
    def _colorArr2Dict(self, colors, yValCnts):
        colorDict = {}
        colors_used = {'m':0,'g':0,'b':0,'y':0,'r':0}

        nColors = len(self.colors)
        start = 0

        for ix, cnt in enumerate(yValCnts):
            cnt = int(cnt)
            currColor = colors[start]

            if currColor not in colorDict:
                colorDict[currColor] = cnt
            else:
                colors_used[currColor] += 1
                keyName = currColor + str(colors_used[currColor])
                colorDict[keyName] = cnt

            start = start + cnt

        return colorDict

    def _sortX(self, coords, yValCnts):
        reOrderCoords = []
        
        start = 0
        for cnt in yValCnts:
            cnt = int(cnt)
            subCoords = coords[start: start + cnt]
            sortedSubCoords = sorted(subCoords, key = lambda column: column[0])
            reOrderCoords.append(sortedSubCoords)
        
            start = start + cnt

        return np.vstack(reOrderCoords)
    
    def _updateFinalCoords(self, coords, oldColors, newColors,  yValCnts):

        colorDict = self._colorArr2Dict(oldColors, yValCnts)
        newColorsCopy = newColors.copy() 
        correctIx = []
        for oldColor, cnt in colorDict.items():
            cnt = int(cnt)
            oldColor = col = re.sub(r'[0-9]+', '', oldColor)
            counter = 0
            for ix, newColor in enumerate(newColorsCopy):
                if newColor == oldColor:
                    correctIx.append(ix)
                    newColorsCopy[ix] = 'Taken'
                    counter += 1
                if counter == cnt:
                    break

        correctedNewColors = [newColors[ix] for ix in correctIx]
        correctedFinalCoords = [coords[ix] for ix in correctIx]
        
        assert(len(correctIx) == len(oldColors))
        assert(oldColors == correctedNewColors)

        correctedFinalCoords = self._sortX(correctedFinalCoords, yValCnts)

        return correctedFinalCoords

    def _getLocalities(self, df, searchLen, normScalar):
        x = df[:, 0].astype(int) // normScalar
        y = df[:, 1].astype(int) // normScalar
        
        xRange = np.max(x) - np.min(x)
        yRange = np.max(y) - np.min(y)
        maxRange = np.max((xRange, yRange))
        
        normSearchLen = searchLen // normScalar
        
        maskDim =  maxRange + 4*normSearchLen
        mask = np.zeros((maskDim, maskDim))
        
        centroids = []
        rewards = []
        localities = []
        
        # draw 1 by 1 organoids on mask with padding
        for ix, coord in enumerate(zip(x, y)):
            cx = coord[0] + 2*normSearchLen
            cy = coord[1] + 2*normSearchLen
            centroids.append((cx,cy))
            mask[cx, cy] = 1
            
            rewards.append(df[:, -1][ix])

        # extract localities 
        for ix, c in enumerate(centroids):
            cx, cy = c[0], c[1]
            locality = mask[cx-normSearchLen: cx+normSearchLen+1, cy-normSearchLen: cy+normSearchLen+1]
            localities.append(np.append(locality.flatten(), rewards[ix]))
            
        return localities
    
    def removal(self, initCoords, finalCoords):

        initNum = len(initCoords)
        finalNum = len(finalCoords)

        if initNum == finalNum:
            print("Move on to matching step")
        elif initNum > finalNum:
            print("Remove from init, holding final fixed")
            new_initCoords = self._removeCentroids(finalCoords, initCoords)
            return new_initCoords, finalCoords
        else:
            print("Remove from final, holding init fixed")
            new_finalCoords = self._removeCentroids(initCoords, finalCoords)
            return initCoords, new_finalCoords

       
        '''DataLog = []
        figRm = plt.figure()
        for i, (x,y) in enumerate(zip(X,Y)):
            plt.scatter(x, y, c = 'b', picker=5)
        def onclick_remove(event):
            event.artist.remove()
            figRm.canvas.draw()
            data = np.frombuffer(figRm.canvas.tostring_rgb(), dtype=np.uint8)
            data = data.reshape(figRm.canvas.get_width_height()[::-1] + (3,))
            DataLog.append(data)
            plt.savefig(os.path.join(self.saveDir, "outputFig.png"), bbox_inches=0, pad_inches = 0)
        cid = figRm.canvas.mpl_connect('pick_event', onclick_remove)
        plt.show()'''
        

    def _removeCentroids(self, refCoords, coordsToRemove): # add colors later?
        # Manually annotate to align color coding of two input patterns
        X = coordsToRemove[:,0]
        Y = coordsToRemove[:,1]
        xyVec = np.array([X,Y]).T
        numCoords = len(X)
        #self._colorVec = colors.copy()
        removeLog = []

        refFig = plt.figure(1)
        plt.scatter(refCoords[:,0], refCoords[:,1]) # , c = colors
        plt.title("REFERENCE IMAGE")

        fig = plt.figure(2, figsize=(8,8))
        for i, (x,y) in enumerate(zip(X,Y)):
            plt.scatter(x, y,  picker=5) #c = colors[i],

        def onclick_remove(event):
            event.artist.remove()

            # get click location
            xclick = np.round(event.mouseevent.xdata,3)
            yclick = np.round(event.mouseevent.ydata, 3)
            clickCoord = np.array((xclick, yclick))

            print('Removing organoid from location: {},{}'.format(xclick, yclick))

            # find index of closest centroid
            clickVec = np.tile(clickCoord, (numCoords, 1))
            diff = clickVec - xyVec
            sumSqDiff = np.sum(diff*diff, axis=1)
            ix = np.argmin(sumSqDiff)
            removeLog.append(ix)

            fig.canvas.draw()

        def on_close(event):
            figNum = event.canvas.figure.number
            print("Figures {} has been closed.".format(figNum))
            self._closedWindows += 1

        cid = fig.canvas.mpl_connect('pick_event', onclick_remove)
        refFig.canvas.mpl_connect('close_event', on_close)
        fig.canvas.mpl_connect('close_event', on_close)
        plt.axis('off')
        plt.show()

        # if both windows close, end return annotation
        if self._closedWindows == 2:
            print("Exiting removal...")
            newCoords = coordsToRemove.copy()
            newCoords = np.delete(newCoords, removeLog, axis = 0)
            self._closedWindows = 0
            return newCoords


    def matching(self, initCoords, finalCoords, searchLen, normScalar, validation = False):
        # main function for matching two patterns

        assert(len(initCoords) == len(finalCoords))
        
        dir_path = os.getcwd()
        saveDir = os.path.join(dir_path, "datasets", self.saveDir)
        if not os.path.exists(saveDir):
            os.makedirs(saveDir)

        # if true, save images to a validation directory to be checked manually
        if validation:
            valDir = os.path.join(saveDir, "validationIms_" + self.saveDir)
            if not os.path.exists(valDir):
                os.makedirs(valDir)
        
        yValCnts = self._numOrgs(initCoords)

        initGrpCoords, finalGrpCoords, colors = self._initColors(initCoords, finalCoords, yValCnts)

        assert(len(initGrpCoords) == len(finalGrpCoords) == len(colors))
        annotColors = self._fixColors(initGrpCoords, finalGrpCoords, colors)
        correctedFinalCoords = np.array(self._updateFinalCoords(finalGrpCoords, colors, annotColors, list(yValCnts)))

        if validation:
            print("Saving validation images in subdirectory...")
            for _ in range(30):
                num = np.random.randint(low = 0, high = len(correctedFinalCoords)-1, size=1) 

                fig, axes = plt.subplots(1,2, figsize=(16,8))
                axes[0].scatter(initGrpCoords[:,0], initGrpCoords[:,1], c=colors)
                axes[0].scatter(initGrpCoords[:,0][num], initGrpCoords[:,1][num], c='black', s=100)

                axes[1].scatter(correctedFinalCoords[:,0], correctedFinalCoords[:,1], c=colors)
                axes[1].scatter(correctedFinalCoords[:,0][num], correctedFinalCoords[:,1][num], c='black', s=100)

                fig.savefig(os.path.join(valDir, "organoid" + str(num)))
                plt.close(fig)

        df = np.hstack((initCoords, correctedFinalCoords))

        print("Saving matched dataframe...")
        np.save(os.path.join(saveDir, "matchDF"), df)

        localities = self._getLocalities(df, searchLen, normScalar)
        print("Saving localities and rewards...")
        np.save(os.path.join(saveDir, "localsAndRewards"), localities)
