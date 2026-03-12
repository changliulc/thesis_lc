# ch4_verify_python.py
# Verify that the GLOBAL configuration reproduces the E1 metrics (IoU>=0.5).
#
# Usage:
#   python ch4_verify_python.py --data_dir <zhenzhi> --synth_dir <synth_out> --gt <parking_groundtruth_filled_cleaned.csv>
#
import argparse, os, re, glob, math
import numpy as np
import pandas as pd
from dataclasses import dataclass
from scipy.signal import lfilter, firwin
from scipy.stats import norm

def cfg_global_v2():
    cfg={}
    cfg['fs']=50.0
    cfg['ev']={'theta_arrive':0.88,'theta_leave':0.25,'arriveLen':6,'arriveWin':4,'leaveLen':5,'leaveWin':6,'Td':4}
    cfg['pr']={'P_vehicle':0.25,'muX':0.0,'muY':0.0,'muZ':0.0,'sigmaX':1.5716,'sigmaY':1.8608,'sigmaZ':0.8196,
               'ema_alpha':0.1,'fir_order':11,'fir_beta':0.5,'fir_fc_xy':5.0,'fir_fc_z':6.0}
    cfg['st']={'L':25,'s':25,'N_stable':5,'R_th':5.43595814555724,'M_th':3.50467962447916}
    cfg['pk']={'T_seek_sec':2.130189771,'D_th':19.520168822607,'D_free':27.1166224036963,'dist_th':20.1886907302364,'lambda_occ':0.224628215628187}
    cfg['dg']={'enable':True,'L_fix':75,'c_th':3}
    cfg['ref']={'enable':True,'alpha_free':0.162018584491401,'D_upd':383.829166434513}
    cfg['v']={'use_mean_diff':True,'use_similarity':True,'use_degrade':True,'use_update_gate':True}
    return cfg

def design_fir(cfg):
    fs=cfg['fs']
    N=cfg['pr']['fir_order']
    beta=cfg['pr']['fir_beta']
    b_xy=firwin(numtaps=N+1, cutoff=cfg['pr']['fir_fc_xy'], fs=fs, window=('kaiser', beta), pass_zero='lowpass', scale=True)
    b_z=firwin(numtaps=N+1, cutoff=cfg['pr']['fir_fc_z'], fs=fs, window=('kaiser', beta), pass_zero='lowpass', scale=True)
    return b_xy, b_z

def ema_filter(x, alpha):
    y=np.empty_like(x)
    y[0]=x[0]
    for i in range(1, len(x)):
        y[i]=alpha*x[i] + (1-alpha)*y[i-1]
    return y

def pr_vehicle(B, cfg, b_xy, b_z):
    x=B[:,0]; y=B[:,1]; z=B[:,2]
    dx=np.empty_like(x); dy=np.empty_like(y); dz=np.empty_like(z)
    dx[0]=0.0; dy[0]=0.0; dz[0]=0.0
    dx[1:]=np.diff(x); dy[1:]=np.diff(y); dz[1:]=np.diff(z)
    dx_lp=lfilter(b_xy, [1.0], dx)
    dy_lp=lfilter(b_xy, [1.0], dy)
    dz_lp=lfilter(b_z, [1.0], dz)
    alpha=cfg['pr']['ema_alpha']
    dx_f=ema_filter(dx_lp, alpha)
    dy_f=ema_filter(dy_lp, alpha)
    dz_f=ema_filter(dz_lp, alpha)
    muX=cfg['pr']['muX']; muY=cfg['pr']['muY']; muZ=cfg['pr']['muZ']
    sigX=cfg['pr']['sigmaX']; sigY=cfg['pr']['sigmaY']; sigZ=cfg['pr']['sigmaZ']
    x1 = 1 - (1 - norm.cdf(np.abs(dx_f), loc=muX, scale=sigX))*2
    y1 = 1 - (1 - norm.cdf(np.abs(dy_f), loc=muY, scale=sigY))*2
    z1 = 1 - (1 - norm.cdf(np.abs(dz_f), loc=muZ, scale=sigZ))*2
    x0 = 1 - x1; y0 = 1 - y1; z0 = 1 - z1
    P_vehicle=cfg['pr']['P_vehicle']; P_env=1-P_vehicle
    pr_env = (x0*y0*z0) / (P_env*P_env)
    pr_veh = (x1*y1*z1) / (P_vehicle*P_vehicle)
    pr = pr_veh / (pr_env + pr_veh)
    return pr

def detect_events(pr, cfg):
    n=len(pr)
    ev=cfg['ev']
    state=1
    i=1
    arriveCount=0; arriveNum=0; arriveleft=1; arriveright=1
    leaveCount=0; leaveNum=0; left=1; right=1
    td=0
    events=[]
    k_in=None
    while i<=n:
        Pr_i=pr[i-1]
        if state==1:
            if Pr_i>=ev['theta_arrive']:
                state=2
                arriveNum=1; arriveCount=1
                arriveleft=i
                arriveright=min(n, i + ev['arriveLen'])
        elif state==2:
            if arriveNum < ev['arriveLen']:
                arriveNum += 1
            if Pr_i >= ev['theta_arrive']:
                arriveCount += 1
            if arriveNum >= ev['arriveLen'] and arriveCount < ev['arriveWin']:
                arriveleft += 1
                if arriveright < n:
                    arriveright += 1
                window=pr[arriveleft-1:arriveright]
                arriveCount = int(np.sum(window >= ev['theta_arrive']))
            if arriveCount == 0:
                state=1
            if arriveCount >= ev['arriveWin']:
                k_in=i
                td=0
                arriveCount=0
                state=3
        elif state==3:
            td += 1
            if td >= ev['Td']:
                state=4
        elif state==4:
            if Pr_i < ev['theta_leave']:
                state=5
                leaveCount=1; leaveNum=1
                left=i
                right=min(n, i + ev['leaveLen'])
        elif state==5:
            if leaveNum < ev['leaveLen']:
                leaveNum += 1
            if Pr_i < ev['theta_leave']:
                leaveCount += 1
            if leaveNum >= ev['leaveLen'] and leaveCount < ev['leaveWin']:
                left += 1
                if right < n:
                    right += 1
                window=pr[left-1:right]
                leaveCount=int(np.sum(window < ev['theta_leave']))
            if leaveCount >= ev['leaveWin']:
                k_out=i
                events.append({'k_in':k_in,'k_out':k_out})
                state=1
                leaveCount=0
        i += 1
    return events

def stability(B, cfg):
    n=B.shape[0]
    L=cfg['st']['L']; s=cfg['st']['s']
    fs=int(cfg['fs'])
    n0=min(n, fs*10)
    sig=np.std(B[:n0,:], axis=0, ddof=1)
    w=np.array([sig[1]*sig[2], sig[0]*sig[2], sig[0]*sig[1]])
    if np.sum(w)==0:
        w=np.array([1.0,1.0,1.0])
    w=w/np.sum(w)
    meanVec=np.full((n,3), np.nan)
    R=np.full(n, np.nan)
    M=np.full(n, np.nan)
    for k in range(L, n+1):
        win=B[k-L:k,:]
        meanVec[k-1,:]=np.mean(win, axis=0)
        rvec=np.max(win, axis=0)-np.min(win, axis=0)
        R[k-1]=float(w.dot(rvec))
        if (k - s) >= L:
            M[k-1]=float(w.dot(np.abs(meanVec[k-1,:]-meanVec[k-s-1,:])))
    stable0=(R <= cfg['st']['R_th']) & (M <= cfg['st']['M_th'])
    Nst=cfg['st']['N_stable']
    stableState=np.zeros(n, dtype=bool)
    cnt=0
    for k in range(1, n+1):
        if stable0[k-1]:
            cnt=min(cnt+1, Nst)
        else:
            cnt=0
        stableState[k-1]=(cnt==Nst)
    return {'meanVec':meanVec,'stableState':stableState}

def run_parking(B, k0, cfg, b_xy, b_z):
    n=B.shape[0]
    pr=pr_vehicle(B,cfg,b_xy,b_z)
    events=detect_events(pr,cfg)
    st=stability(B,cfg)
    seekN=int(round(cfg['pk']['T_seek_sec']*cfg['fs']))
    FREE=0; OCC=1
    state=FREE
    stable_indices=np.where(st['stableState'])[0]
    if stable_indices.size>0:
        kk=stable_indices[0]+1
        S_pre=st['meanVec'][kk-1,:].copy()
    else:
        S_pre=B[0,:].copy()
    S_post=None; dB=None
    c_park=0; c_free=0
    pred_k=[]; conf_k=[]
    open_k_in=np.nan; open_k_conf_in=np.nan
    for e in events:
        k_out=int(e['k_out'])
        if state==FREE and cfg['ref']['enable']:
            idx=np.where(st['stableState'][:k_out])[0]
            if idx.size>0:
                k_last=idx[-1]+1
                S_cand=st['meanVec'][k_last-1,:]
                alpha=cfg['ref']['alpha_free']
                d=S_cand - S_pre
                nd=float(np.linalg.norm(d))
                if not cfg['v']['use_update_gate']:
                    S_pre=(1-alpha)*S_pre + alpha*S_cand
                else:
                    if nd <= cfg['ref']['D_upd']:
                        S_pre=(1-alpha)*S_pre + alpha*S_cand
                    else:
                        if nd>0:
                            S_pre=S_pre + alpha*(cfg['ref']['D_upd']/nd)*d
        k_seek_end=min(n, k_out + seekN)
        slice_st=st['stableState'][k_out-1:k_seek_end]
        found=np.where(slice_st)[0]
        if found.size>0:
            k_st=k_out + int(found[0])
            S_new=st['meanVec'][k_st-1,:]
            stable_found=True
        else:
            k_st=None; S_new=None; stable_found=False
        if state==FREE:
            if stable_found:
                dB_cand=S_new - S_pre
                drift_mag=float(np.linalg.norm(dB_cand))
                if drift_mag > cfg['pk']['D_th']:
                    state=OCC
                    S_post=S_new.copy()
                    dB=dB_cand.copy()
                    open_k_in=k_out
                    open_k_conf_in=k_st
                    c_park=0; c_free=0
            else:
                if cfg['dg']['enable'] and cfg['v']['use_degrade']:
                    if (k_seek_end - cfg['dg']['L_fix'] + 1) >= 1:
                        start=k_seek_end - cfg['dg']['L_fix'] + 1
                        S_hat=np.mean(B[start-1:k_seek_end,:], axis=0)
                    else:
                        S_hat=np.mean(B[:k_seek_end,:], axis=0)
                    dB_hat=S_hat - S_pre
                    drift_mag=float(np.linalg.norm(dB_hat))
                    if drift_mag > cfg['pk']['D_th']:
                        c_park=min(c_park+1, cfg['dg']['c_th'])
                    else:
                        c_park=0
                    if c_park >= cfg['dg']['c_th']:
                        state=OCC
                        S_post=S_hat.copy()
                        dB=dB_hat.copy()
                        open_k_in=k_out
                        open_k_conf_in=k_seek_end
                        c_park=0; c_free=0
        else:
            if stable_found:
                back2env=float(np.linalg.norm(S_new - S_pre))
                if back2env < cfg['pk']['D_free']:
                    state=FREE
                    pred_k.append([open_k_in,k_out])
                    conf_k.append([open_k_conf_in,k_st])
                    S_pre=S_new.copy()
                    open_k_in=np.nan; open_k_conf_in=np.nan
                    S_post=None; dB=None
                    c_free=0
                else:
                    dist=np.nan
                    if cfg['v']['use_similarity'] and dB is not None:
                        dist=float(np.linalg.norm((S_new - S_pre) - dB))
                    if (not np.isnan(dist)) and dist < cfg['pk']['dist_th']:
                        S_post=(1-cfg['pk']['lambda_occ'])*S_post + cfg['pk']['lambda_occ']*S_new
                        dB=S_post - S_pre
                        c_free=0
                    else:
                        c_free=min(c_free+1, cfg['dg']['c_th'])
                        if c_free >= cfg['dg']['c_th']:
                            state=FREE
                            pred_k.append([open_k_in,k_out])
                            conf_k.append([open_k_conf_in,k_st])
                            S_pre=S_new.copy()
                            open_k_in=np.nan; open_k_conf_in=np.nan
                            S_post=None; dB=None
                            c_free=0
            else:
                if cfg['dg']['enable'] and cfg['v']['use_degrade']:
                    if (k_seek_end - cfg['dg']['L_fix'] + 1) >= 1:
                        start=k_seek_end - cfg['dg']['L_fix'] + 1
                        S_hat=np.mean(B[start-1:k_seek_end,:], axis=0)
                    else:
                        S_hat=np.mean(B[:k_seek_end,:], axis=0)
                    back2env=float(np.linalg.norm(S_hat - S_pre))
                    if back2env < cfg['pk']['D_free']:
                        c_free=min(c_free+1, cfg['dg']['c_th'])
                    else:
                        c_free=0
                    if c_free >= cfg['dg']['c_th']:
                        state=FREE
                        pred_k.append([open_k_in,k_out])
                        conf_k.append([open_k_conf_in,k_seek_end])
                        S_pre=S_hat.copy()
                        open_k_in=np.nan; open_k_conf_in=np.nan
                        S_post=None; dB=None
                        c_free=0
    return np.array(pred_k,dtype=float), np.array(conf_k,dtype=float), events

def postprocess(pred, fs, Tmin_sec=0.0, gap_merge_sec=0.0):
    pred=np.array(pred, dtype=float).reshape((-1,2))
    if pred.size==0:
        return pred.reshape((0,2))
    dur=(pred[:,1]-pred[:,0])/fs
    pred=pred[dur>=Tmin_sec]
    if pred.size==0 or gap_merge_sec<=0:
        return pred.reshape((-1,2))
    pred=pred[np.argsort(pred[:,0])]
    gap_k=int(round(gap_merge_sec*fs))
    merged=[pred[0].tolist()]
    for i in range(1,pred.shape[0]):
        if pred[i,0] - merged[-1][1] <= gap_k:
            merged[-1][1]=max(merged[-1][1], pred[i,1])
        else:
            merged.append(pred[i].tolist())
    return np.array(merged, dtype=float)

def eval_iou(pred, gt, iou_th=0.5):
    pred=np.array(pred, dtype=float).reshape((-1,2))
    gt=np.array(gt, dtype=float).reshape((-1,2))
    Np=pred.shape[0]; Ng=gt.shape[0]
    if Np==0 and Ng==0:
        TP=FP=FN=0
    elif Np==0 and Ng>0:
        TP=0; FP=0; FN=Ng
    elif Np>0 and Ng==0:
        TP=0; FP=Np; FN=0
    else:
        IoU=np.zeros((Np,Ng))
        for i in range(Np):
            for j in range(Ng):
                inter=max(0.0, min(pred[i,1], gt[j,1]) - max(pred[i,0], gt[j,0]))
                uni=max(pred[i,1], gt[j,1]) - min(pred[i,0], gt[j,0])
                if uni>0:
                    IoU[i,j]=inter/uni
        pairs=[(i,j,IoU[i,j]) for i in range(Np) for j in range(Ng)]
        pairs.sort(key=lambda x: -x[2])
        matched_p=np.zeros(Np, dtype=bool)
        matched_g=np.zeros(Ng, dtype=bool)
        match=[]
        for i,j,v in pairs:
            if v < iou_th:
                break
            if (not matched_p[i]) and (not matched_g[j]):
                matched_p[i]=True; matched_g[j]=True
                match.append((i,j,v))
        TP=len(match)
        FP=int(np.sum(~matched_p))
        FN=int(np.sum(~matched_g))
    P=TP/max(TP+FP,1)
    R=TP/max(TP+FN,1)
    F1=2*P*R/max(P+R, np.finfo(float).eps)
    return TP,FP,FN,P,R,F1

def append_synth_gt_all_events(gt_df, synth_dir):
    gt2=gt_df.copy()
    synth_files=glob.glob(os.path.join(synth_dir,'*_synth.csv'))
    for path in synth_files:
        fname=os.path.basename(path)
        if '_B_synth' in fname: g='B'
        elif '_C_synth' in fname: g='C'
        elif '_D_synth' in fname: g='D'
        else: continue
        m=re.match(r'^(.*)_e\d+_[BCD]_synth\.csv$', fname)
        if not m: continue
        baseStem=m.group(1)
        cand=[f"{baseStem}_clean_crop.csv", f"{baseStem}_clean.csv"]
        baseFile=None
        for c in cand:
            if (gt2['file']==c).any():
                baseFile=c; break
        if baseFile is None:
            continue
        base=gt2[gt2['file']==baseFile].copy()
        if base.empty:
            continue
        gt2=gt2[gt2['file']!=fname].copy()
        r=base.copy()
        r['file']=fname
        if 'scenario_group' in r.columns:
            r['scenario_group']=g
        if 'notes' in r.columns:
            r['notes']='synth_all_events'
        gt2=pd.concat([gt2, r], ignore_index=True)
    return gt2

def find_csv(fileName, data_dir, synth_dir):
    cand=os.path.join(data_dir, fileName)
    if os.path.exists(cand):
        return cand
    cand=os.path.join(synth_dir, fileName)
    if os.path.exists(cand):
        return cand
    return None

def load_csv(csv_path, fs=50.0):
    T=pd.read_csv(csv_path)
    if 'k' not in T.columns:
        T['k']=np.arange(len(T))
    if 't' not in T.columns:
        T['t']=T['k']/fs
    B=T[['x','y','z']].to_numpy(dtype=float)
    return T['k'].to_numpy(dtype=float), T['t'].to_numpy(dtype=float), B

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data_dir', required=True)
    ap.add_argument('--synth_dir', required=True)
    ap.add_argument('--gt', required=True)
    args=ap.parse_args()

    cfg=cfg_global_v2()
    # match your current global overrides
    cfg['pk']['D_th']=36.0
    cfg['pk']['dist_th']=4.0
    cfg['ref']['D_upd']=30.0

    Tmin_sec=6.0
    gap_merge_sec=0.0
    IOU_TH=0.5

    b_xy,b_z=design_fir(cfg)

    gt_base=pd.read_csv(args.gt)
    gt_all=append_synth_gt_all_events(gt_base, args.synth_dir)
    files=sorted(gt_all['file'].unique())

    sumBy={g:{'TP':0,'FP':0,'FN':0} for g in ['A','B','C','D']}
    sumAll={'TP':0,'FP':0,'FN':0}
    events_cnt=pred_cnt=gt_cnt=0

    for fileName in files:
        csvPath=find_csv(fileName, args.data_dir, args.synth_dir)
        k,t,B=load_csv(csvPath, cfg['fs'])
        pred_k, conf_k, events = run_parking(B, k[0], cfg, b_xy, b_z)
        pred_k = postprocess(pred_k, cfg['fs'], Tmin_sec, gap_merge_sec)

        gt_f=gt_all[gt_all['file']==fileName]
        gname=str(gt_f['scenario_group'].iloc[0])
        k0=k[0]
        gt_idx=np.column_stack([gt_f['k_star_in'].to_numpy()-k0+1, gt_f['k_star_out'].to_numpy()-k0+1])

        TP,FP,FN,P,R,F1=eval_iou(pred_k, gt_idx, IOU_TH)

        sumBy[gname]['TP']+=TP; sumBy[gname]['FP']+=FP; sumBy[gname]['FN']+=FN
        sumAll['TP']+=TP; sumAll['FP']+=FP; sumAll['FN']+=FN

        events_cnt += len(events); pred_cnt += pred_k.shape[0]; gt_cnt += gt_idx.shape[0]
        print(f"File={fileName} | Group={gname} | TP={TP} FP={FP} FN={FN} | F1={F1:.3f} | events={len(events)} pred={pred_k.shape[0]} gt={gt_idx.shape[0]} | Tmin={Tmin_sec:.2f}")

    def prf(TP,FP,FN):
        P=TP/max(TP+FP,1); R=TP/max(TP+FN,1); F1=2*P*R/max(P+R,1e-12); return P,R,F1

    print("\n=== By Group (IoU>=0.50) ===")
    for g in ['A','B','C','D']:
        P,R,F1=prf(sumBy[g]['TP'],sumBy[g]['FP'],sumBy[g]['FN'])
        print(f"Group={g} | P={P:.3f} R={R:.3f} F1={F1:.3f} | FP={sumBy[g]['FP']} FN={sumBy[g]['FN']}")
    P,R,F1=prf(sumAll['TP'],sumAll['FP'],sumAll['FN'])
    print(f"\nAll | P={P:.3f} R={R:.3f} F1={F1:.3f} | FP={sumAll['FP']} FN={sumAll['FN']}")
    print(f"files={len(files)}, events={events_cnt}, pred={pred_cnt}, gt={gt_cnt}")

if __name__=='__main__':
    main()