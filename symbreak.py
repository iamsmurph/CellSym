import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from scipy import ndimage
import pickle
from sklearn.preprocessing import MinMaxScaler
import argparse
import os
import torch
from PIL import Image
#import cupyx.scipy.ndimage.gaussian_filter 

class SymBreak:
    def __init__(self, 
            data_path,
            save_path,
            save_plots,
            pad = 700, # padding in microns
            org_rad = 75, # organoid radius in microns
        ):
        self.data_path = data_path
        self.save_path = save_path
        self.save_plots = save_plots
        self.pad = pad
        self.org_rad = org_rad

        model_path = "models/krr_model.pkl"
        scaler_path = "models/scaler.pkl"
        loaded_model = pickle.load(open(model_path, 'rb'))
        loaded_scaler = pickle.load(open(scaler_path,'rb'))

        centroids = pd.read_csv(self.data_path, header=None).values.astype(int)
        self.centroids = self.shift(centroids)

        self.model = loaded_model
        self.scaler = loaded_scaler

    def predict_dipole(self):   
        feats = self.get_features(self.centroids)
        X = self.scaler.transform(feats)

        print("Making predictions..")
        preds = self.model.predict(X)

        preds = preds.reshape(-1, 1)

        if self.save_plots:
            self.make_plot(self.centroids, preds)

        res_arr = np.hstack([self.centroids, feats, preds])

        cols = ["cx", "cy","grad_200","density_700","pred"]
        res_df = pd.DataFrame(res_arr, columns = cols)
        pth = os.path.join(self.save_path, "pred_results_df.csv")
        res_df.to_csv(pth, index=False) 
        return res_df

    def get_features(self, centroids):
            mask = self.make_mask(centroids)

            # make mask for pattern
            print("Generating mask..")
            im = self.make_pattern(mask, centroids).astype(np.uint8)

            if self.save_plots:
                save_im = Image.fromarray(im)
                pth = os.path.join(self.save_path, "organoid_coordinates.jpeg")
                save_im.save(pth)            

            print("Computing features..This step is slow, please wait")
            # Gaussian blur
            im_blurs = []
            sigmas = [200, 700]
            for sigma in tqdm(sigmas):
                blur = ndimage.gaussian_filter(im, sigma=sigma) #, mode="constant"
                im_blurs.append(blur)
        
            # get features of organoids
            grad_rho200 = self.compute_feats(im, im_blurs[0], centroids, rho = False)
            rho700 = self.compute_feats(im, im_blurs[1], centroids, grad_rho = False)
            feats = np.array(list(zip(grad_rho200, rho700)))
            return feats
        
    def compute_feats(self, im, im_blur, centroids, rho = True, grad_rho = True):
        feats = []
        for x, y in centroids:
            bool_mat = self.circle(x,y, im, self.org_rad)
            dfeats = im_blur[bool_mat]
            if rho and not grad_rho:
                density = np.mean(dfeats)
                feats.append(density)
            if not rho and grad_rho:
                grad, _ = self.max_gradient(x,y, im_blur)
                feats.append(grad)
            if rho and grad_rho:
                feats.append((density, grad))
        return feats
                

    def max_gradient(self, x,y, im_blur):
        # get pixel intensities in extremes
        xmax = im_blur[x + self.org_rad - 1, y]
        xmin = im_blur[x - self.org_rad, y]
        ymax = im_blur[x, y + self.org_rad - 1]
        ymin = im_blur[x, y - self.org_rad]

        xdiffnorm  = ((int(xmax) - int(xmin)) / self.org_rad)
        ydiffnorm = ((int(ymax) - int(ymin)) / self.org_rad)

        # gradient magnitude and vector
        grad = np.array(np.sqrt(xdiffnorm**2 + ydiffnorm**2))
        gradVec = np.array((xdiffnorm, ydiffnorm))
                    
        return grad, gradVec

    def make_plot(self, centroids, preds):
        mask = self.make_mask(centroids)
        im_pred = self.make_pattern(mask, centroids, preds = preds)
        plt.imshow(im_pred)
        #save_im = Image.fromarray(im_pred)
        pth = os.path.join(self.save_path, "organoid_dipole_predictions.jpeg")
        plt.savefig(pth) 

    def make_mask(self, centroids):
        cmax = np.max(centroids)
        size = cmax + self.pad
        mask = np.zeros((size, size)) 
        return mask

    def shift(self, centroids):
        cmin, cmax = np.min(centroids), np.max(centroids)
        diff = max(0, self.pad - cmin)
        centroids += diff
        return centroids

    def make_pattern(self, mask, centroids, preds = None):
        if preds is None:
            cols = [255]*len(centroids)
        else:
            cols = preds

        for (x,y), c in zip(centroids, cols):
            dim = len(mask)
            xx, yy = np.mgrid[:self.org_rad*2, :self.org_rad*2]
            zz = (xx - self.org_rad) ** 2 + (yy - self.org_rad) ** 2
            circle = zz < self.org_rad ** 2
            bool_mat = np.pad(circle, ((x-self.org_rad, dim-x-self.org_rad),(y-self.org_rad, dim-y-self.org_rad)))
            mask[bool_mat] = c
        
        return mask           

    def circle(self, x,y, orgIm, radius, fill = False, fillVal = 255):
        dim = len(orgIm)
        xx, yy = np.mgrid[:radius*2, :radius*2]
        zz = (xx - radius) ** 2 + (yy - radius) ** 2
        circle = zz < radius ** 2
        
        bool_mat = np.pad(circle, ((x-radius, dim-x-radius),(y-radius, dim-y-radius)))
        if fill:
            orgIm[bool_mat] = fillVal
            return orgIm
        else:
            return bool_mat

    # anneal
        # save coords/annealed points 
        # save plot of coords and annealed coords

    