# Localizing ground mobile robots with a fixed external / overhead camera: fiducial markers vs. markerless deep learning

Context: these notes support positioning a new system, in which one overhead webcam localizes a small 4-wheel omni robot (x, y, heading) on the floor with a YOLO-style detector and feeds that pose back for closed-loop control.

Verification legend:
- **[V]**: details checked this session on the source page or its abstract/arXiv page.
- **[S]**: taken from a search-engine snippet or secondary summary; the full text was not opened.
- **[U]**: not verified. Check before citing.

DOIs are given only when a source page showed them. A DOI built from a URL pattern is marked as such.

---

## Q1. How accurate are ArUco/AprilTag (fiducial) overhead localization systems for mobile robots? Typical position/heading error, frame rate, failure modes

### Takeaway
A calibrated fixed overhead camera tracking fiducials (or active LEDs) usually gets **about 1 cm position error and under 1° heading error** at 30-50 Hz on table- or room-sized arenas (2-5 m). The main failure modes reported are lighting changes and reflections, which need recalibration; occlusion and loss of tracks; computation load as robot count grows; and noise under motion. Motion capture (Vicon, under 1 mm) replaced webcam+ArUco at the Robotarium for exactly these robustness reasons.

### Cited Findings

**Robotarium (Georgia Tech): webcam + ArUco, later Vicon** [V for the camera description; accuracy figures S]
- Pickem, Lee, Ames, Egerstedt et al., "Safe, Remote-Access Swarm Robotics Research on the Robotarium," arXiv:1604.00640 (2016, earlier/seminal), and "The Robotarium: A remotely accessible swarm robotics research testbed," IEEE ICRA 2017 (PDF: http://ames.caltech.edu/robotarium-icra_2017.pdf). The overhead tracking used standard webcams (Microsoft LifeCam Studio HD); one webcam plus ArUco tags tracked the robots. An older project page claims update rates up to 30 Hz. I found no accuracy figure for the webcam version. — [arXiv 1604.00640](https://arxiv.org/pdf/1604.00640); [ICRA 2017 PDF](http://ames.caltech.edu/robotarium-icra_2017.pdf)
- Failure modes the Robotarium team reported: the computation needed for visual tracking grew with the number of agents; the camera "often required recalibration through the day due to changing ambient light conditions"; and tracks of individual robots were lost "due to obstruction or reflections." This led to the move to a Vicon Vantage V16 motion-capture system. — [Robotarium testbed paper (IEEE AAM PDF)](https://ieeexplore.ieee.org/ielaam/9552933/9973428/9996578-aam.pdf) [S]. Title as listed: "The Robotarium: A Remotely-Accessible, Multi-Robot Testbed for Control Research and Education" (Wilson et al.?, ~2022). Authors and venue [U]: confirm on the IEEE page.
- A 2024 survey reports that the Robotarium and IDS3C (both Vicon-based) have localization errors below 1 mm. — [Survey on Small-Scale Testbeds for CAVs and Robot Swarms, arXiv 2408.14199](https://arxiv.org/pdf/2408.14199) [S]. The full text was too large to fetch, so authors and venue are [U].

**HeRoSwarm (2022): overhead camera + AprilTag** [S]
- HeRoSwarm miniature swarm robot, arXiv:2211.03014. An overhead camera server watches a 2.5 × 1.75 m tabletop, and each robot carries one AprilTag on its top plate. The camera-based positioning system has a reported **average error of 0.8 cm** and is used as ground truth. Robot odometry drifts up to 12.8 cm relative to it. The source does not say which computer runs detection. — [arXiv 2211.03014](https://arxiv.org/pdf/2211.03014)

**CPM Lab (RWTH Aachen): ceiling camera + active LEDs (a non-fiducial marker baseline)** [S, well corroborated]
- Kloock, Scheffe, Tülleners, Maczijewski, Kowalewski, Alrifaee, "Vision-Based Real-Time Indoor Positioning System for Multiple Vehicles," arXiv:2002.05755 (2020). The British Library catalog lists it as "Issue 2 (2020)", probably IFAC-PapersOnLine 53(2) from IFAC World Congress 2020 [U]. One ceiling camera at 3.3 m height tracks LED patterns on up to 20 model cars on a 4 × 4.5 m map. Mean errors are **about 1.1 cm in position and about 0.6° in orientation**. Pose updates run at **50 Hz** with a 20 ms soft real-time deadline and about 100 µs exposure. The authors say the system is robust to changing light and reflections because the LEDs are active and exposure is short. — [arXiv 2002.05755](https://ar5iv.labs.arxiv.org/html/2002.05755); [CPM Lab page](https://cpm.lrt.unibw.de/indoor-positioning-system/)

**Duckietown Autolab: fixed "Watchtowers" + AprilTags** [S]
- A network of low-cost Watchtowers (the same camera and compute as a Duckiebot) with overlapping fields of view. Each one detects AprilTags on the robots and on fixed road-layer calibration tags, which give the camera-to-map transform. Poses are fused by pose-graph optimization. I found no mm/cm accuracy number. A community repository notes that the full pose graph is accurate but slow, and that a faster projection method shows a fixed offset that needs measuring at startup. — [Integrated Benchmarking..., arXiv 2009.04362](https://arxiv.org/pdf/2009.04362); [arXiv 2305.09848](https://arxiv.org/pdf/2305.09848); [Duckietown Autolab docs](https://docs.duckietown.com/ente/opmanual-autolab/localization.html)

**Benchmarks comparing marker families**
- Kalaitzakis, Cain, Carroll, Ambrosi, Vitzilaios, "Fiducial Markers for Pose Estimation: Overview, Applications and Experimental Comparison of the ARTag, AprilTag, ArUco and STag Markers," *Journal of Intelligent & Robotic Systems* 101(4), 2021, **DOI 10.1007/s10846-020-01307-9** [V for the DOI, via the Springer DOI link]. It compares accuracy, detection rate and compute cost across scenarios that include simulated shadows and motion blur. A secondary summary says AprilTag has the best detection rate and ARTag a consistently low one; AprilTag, ArUco and STag are above 90% detection except in one case. — [Springer DOI](https://link.springer.com/doi/10.1007/s10846-020-01307-9); [ResearchGate listing](https://www.researchgate.net/publication/350418791_Fiducial_Markers_for_Pose_Estimation_Overview_Applications_and_Experimental_Comparison_of_the_ARTag_AprilTag_ArUco_and_STag_Markers) [S; the numeric tables were not seen because the Springer page is paywalled/redirected]
- FMAC, "a Fair Fiducial Marker Accuracy Comparison Software," arXiv:2601.07723 (2026). Detection rates: ArUco 100%, AprilTag 99.74%, STag 84.27%. AprilTag has the best angular accuracy (about 0.1°); STag's translation error is similar but its angular standard deviation is higher. — [arXiv 2601.07723](https://arxiv.org/html/2601.07723v1) [S]
- Under occlusion, one study reports detection rates of 80% for BlobBoards, 74% for AprilTag and 58% for ArUco. I did not identify which study this is [U]. — via [search summary](https://arxiv.org/html/2601.07723v1) [S]

**Ceiling-mounted ArUco (camera on the robot looking up, i.e. the reverse geometry, used only as contrast)**
- GroundGazer (below) cites Hinderer et al. (ICAR 2025 submission), which reached "low cm accuracy" with ceiling ArUco at large camera-to-marker distances. — [arXiv 2509.17346](https://arxiv.org/html/2509.17346v1) [V]
- Accuracy degrades with distance and smaller marker size; one study found good accuracy only up to about 100 cm from the marker. — [Babinec et al., ResearchGate](https://www.researchgate.net/publication/270107591_Visual_Localization_of_Mobile_Robot_Using_Artificial_Markers) [S, older]
- ArUco pose measurements became noisy under some motion conditions (upward camera seeing a ceiling marker). — [arXiv 2505.00842](https://arxiv.org/pdf/2505.00842) [S]

**Detection speed of fiducials**
- Romero-Ramirez, Muñoz-Salinas, Medina-Carnicer, "Speeded up detection of squared fiducial markers," *Image and Vision Computing* 76:38-47, 2018, **DOI 10.1016/j.imavis.2018.05.004**. The multi-scale ArUco detector is up to 40× faster than the prior state of the art, with over 1000 fps on 4K images without parallelization. — [URJC repository](https://burjcdigital.urjc.es/handle/10115/42233) [S, the DOI is from the search summary]
- PhotonVision's FRC guide says AprilTag detection is CPU-bound and commonly runs on a Raspberry Pi 4/5. It recommends calibrating at the running resolution, with reprojection error under about 1 px. — [LearnFRC/PhotonVision guide](https://learnfrc.com/blog/frc-photonvision-setup) [S, grey literature]

### Inferences
- A realistic marker-based baseline for a single overhead webcam on a 1-3 m floor area is **about 0.5-1.5 cm position and about 0.5-1° heading** at 30 Hz. HeRoSwarm (0.8 cm) and CPM Lab (1.1 cm / 0.6°, though with LEDs and a high-end camera) bracket this range.
- A YOLO-based markerless system should be compared against this baseline. It probably will not beat fiducials on raw accuracy, but it can claim no marker on the robot, robustness to a partly occluded or dirty tag, and reuse of an existing camera. The Robotarium's lighting and reflection problems are a documented motivation for alternatives.
- ArUco or AprilTag remain the natural ground-truth or reference method for evaluating a YOLO system if no motion capture is available.

### Gaps
- The Kalaitzakis 2021 per-marker numeric errors (cm, deg, ms) were not retrieved because of the paywall.
- I found no peer-reviewed accuracy figure for the Robotarium's original webcam+ArUco tracker.
- Duckietown Watchtower localization accuracy was not found in the fetched material.
- I found few studies that quantify motion blur at a given robot speed for overhead tags specifically.

---

## Q2. What markerless deep-learning methods detect a robot and estimate its pose/heading from a fixed camera, and how do they compare with markers?

### Takeaway
Few works address markerless localization of a ground robot from a fixed external camera. The two strongest are Bultmann et al. (ICRA 2023: detector + keypoints + PnP, multi-camera, about 2.9 cm / 0.9°) and Robinson et al. (IROS 2023: YOLOv5 box + CNN orientation classifier/regressor, about 2.2-2.9° median heading, closed-loop control). Neither benchmarks directly against fiducials, and **I found no published work using YOLO-OBB or YOLO-pose for overhead mobile-robot pose**. This is a clear gap the new system can fill.

### Cited Findings

**Bultmann, Memmesheimer, Behnke, "External Camera-based Mobile Robot Pose Estimation for Collaborative Perception with Smart Edge Sensors," IEEE ICRA 2023, London** [V via arXiv]
- arXiv:2303.03797. The publisher DOI was not shown on the pages fetched. — [arXiv/ar5iv](https://ar5iv.labs.arxiv.org/html/2303.03797); [PDF](https://www.ais.uni-bonn.de/papers/ICRA_2023_Bultmann.pdf)
- Setup: 4 static smart edge sensors at about 2.5 m height in a cluttered room of about 240 m², each running on an Nvidia Jetson Xavier NX. The robot is a Toyota HSR.
- Method: MobileDet detects the robot in 848×480 images. A MobileNetV3-based keypoint network on 192×256 crops predicts 2D projections of manually defined 3D keypoints on the rigid base; it is trained only on synthetic data (36k samples). Multi-view reprojection-error minimization (Ceres LM) follows, with PnP initialization, a bearing-only outlier heuristic and pose-graph fusion with odometry. The paper says the method "does not require attaching fiducial markers to the robot."
- Results, with HTC Vive ground truth: fused translation error **2.93 cm** (4.25 cm with 1 camera, 2.64 cm with 2, 2.73 cm with 4) and orientation **0.88°**. The robot's own navigation localization averaged 19.1 cm / 1.11°. Long trajectories succeeded 5/5 with camera correction versus 1/5 without.
- Frame rate of the camera pipeline: not reported. There is no direct comparison against markers.

**Robinson, De Martini, Gadd, Newman, "Visual Servoing on Wheels: Robust Robot Orientation Estimation in Remote Viewpoint Control," IROS 2023 (accepted)** [V via arXiv HTML]
- arXiv:2306.14848, DOI 10.48550/arXiv.2306.14848 (arXiv DOI). — [arXiv](https://arxiv.org/abs/2306.14848); [HTML](https://arxiv.org/html/2306.14848)
- Camera: a single **Logitech C270 HD webcam** on a tripod at about 2.3 m, in an oblique remote view. Robot: TurtleBot with a Raspberry Pi 4 that only relays commands. Computation runs off-board on a laptop (Ryzen 9 5900HS, RTX 3050 Ti).
- Method: **YOLOv5** detects the robot's bounding box. A crop goes to an EfficientNet-based orientation head with 100 angle bins. The expected (cos, sin) over the bins is passed through atan2 to give full 360° heading. The loss combines MSE (with wrap-around) and cross-entropy. Training data is generated by weak supervision with no manual angle labels; pure regression was the worst baseline. It assumes no markers and no known robot size or colour.
- Heading error (median): **2.16°-2.90°** across 5 indoor environments. The ground truth is approximate, built from box-to-box motion vectors.
- Position: image-space bounding box only, with **no camera calibration or homography**.
- Frame rate: not reported. Setup time: under 30 min.
- There is no quantitative comparison to fiducials; the paper only positions itself against LED, feature-point and floor-marker methods.

**Markerless camera-to-robot pose (manipulators, for method lineage)** [S]
- DREAM (Lee et al., "Camera-to-Robot Pose Estimation from a Single Image," arXiv:1911.09231, ICRA 2020 [U venue]): per-keypoint belief maps followed by PnP. — [ar5iv 1911.09231](https://ar5iv.labs.arxiv.org/html/1911.09231)
- CtRNet (Lu et al., "Markerless Camera-to-Robot Pose Estimation via Self-supervised Sim-to-Real Transfer," CVPR 2023): segmentation + keypoints + PnP, self-supervised sim-to-real, high-speed inference. — [CVF open access](https://openaccess.thecvf.com/content/CVPR2023/papers/Lu_Markerless_Camera-to-Robot_Pose_Estimation_via_Self-Supervised_Sim-to-Real_Transfer_CVPR_2023_paper.pdf)
- CtRNet-X (2024): handles partially visible robots using VLM-detected components. — [arXiv 2409.10441](https://arxiv.org/pdf/2409.10441)

**Oriented bounding boxes (OBB): closest analogue, from grasping** [S]
- "Object detection using YOLO oriented bounding box for robot grasping applications," ScienceDirect, 2026. YOLOv11-OBB gives in-plane rotation plus position, running on a GPU laptop. — [ScienceDirect S2666307426000161](https://www.sciencedirect.com/science/article/pii/S2666307426000161) [authors and venue U]
- The Ultralytics YOLO26 paper notes that earlier YOLO-OBB models follow the OpenCV angle convention, an acute angle in (0, 90°]. That is **ambiguous for 360° heading**, so the front of the robot must be resolved separately (keypoints, an asymmetric cue, or class). — [arXiv 2606.03748](https://arxiv.org/html/2606.03748v1) [S]
- Ultralytics pose models output K keypoints per instance (pixel and normalized), and pretrained weights cover 17 human COCO joints, so custom robot keypoints need training. — [Ultralytics pose docs](https://docs.ultralytics.com/tasks/pose) [S]

**Older ceiling-image CNN (onboard, contrast only)**
- A CNN on ceiling images (camera on the robot looking up) regresses pose; occlusion of the ceiling dominates its error. — [SCITEPRESS 2021](https://www.scitepress.org/Papers/2021/102484/102484.pdf) [S, out of scope]

### Inferences
- Accuracy ranking from the evidence: active LED or fiducial overhead (about 1 cm / 0.6-1°) ≈ multi-camera keypoint+PnP (about 2.9 cm / 0.9°), both better than single-camera YOLO + orientation CNN (about 2-3° median heading, position not separately reported).
- For an omni robot, heading matters mainly for the body-frame velocity transform, not for nonholonomic steering, so heading errors of 2-3° may be acceptable. The paper can argue this.
- A YOLO-pose model with 2 keypoints (front/back) or an OBB plus a front keypoint would resolve the OBB 90° ambiguity. No published overhead mobile-robot paper does this yet, which supports a novelty claim (this is my inference from the search, not proof of absence).

### Gaps
- I found no paper reporting **detection mAP** for an overhead mobile-robot detector.
- I found no head-to-head experiment that runs a markerless detector and ArUco/AprilTag on the same overhead robot under the same conditions.
- MDPI "YOLOv8-PoseBoost" (Electronics 13(6):1046) mentions robot pose keypoints, but the snippet gave no robot heading details. — [MDPI](https://www.mdpi.com/2079-9292/13/6/1046) [U]

---

## Q3. Works running such localization on CPU-only / low-cost hardware (Raspberry Pi, laptop CPU, OpenVINO, ONNX)

### Takeaway
Low-cost hardware is common in the **marker-based** and pattern-based systems (webcams, Raspberry Pi 4, under $100-500). Markerless deep-learning systems in the literature use GPUs or Jetsons: Bultmann on Jetson Xavier NX, Robinson on a laptop with an RTX 3050 Ti. **I found no paper reporting markerless overhead robot localization on CPU only (OpenVINO/ONNX)**, which is a gap the new system can claim.

### Cited Findings
- **GroundGazer** (Hinderer, Hüsken, Sun, Yang, University of Stuttgart), "GroundGazer: Camera-based indoor localization of mobile robots with millimeter accuracy at low cost," arXiv:2509.17346, Sep 2025 (preprint). This is an **onboard** floor-facing fisheye camera (contrast only). The total cost is under $500, including a Raspberry Pi 4 and a camera under $100, compared with commercial systems above $1000. MAE: x 0.93 mm, y 0.82 mm, θ 0.49° (95th percentile 3.29 mm / 1.96 mm / 1.24°). It runs at 8.33 Hz (not yet real-time); the maximum speed is about 0.69 m/s before aliasing. Failure modes: vibration or uneven ground causing heading outliers, jumps between squares at speed, and QR masking. — [arXiv 2509.17346](https://arxiv.org/html/2509.17346v1) [V]
- Robotarium (original): consumer Microsoft LifeCam webcams + ArUco. — [ICRA 2017 PDF](http://ames.caltech.edu/robotarium-icra_2017.pdf) [S]
- Duckietown Watchtowers: "low-cost observation structures using the same sensing and computation as the Duckiebots" (Raspberry Pi-class). — [arXiv 2009.04362](https://arxiv.org/pdf/2009.04362) [S]
- Robinson et al. 2023: a $20-30-class Logitech C270 webcam, but inference runs on an RTX 3050 Ti laptop. — [arXiv HTML 2306.14848](https://arxiv.org/html/2306.14848) [V]
- Bultmann et al. 2023: Jetson Xavier NX per camera. — [ar5iv 2303.03797](https://ar5iv.labs.arxiv.org/html/2303.03797) [V]
- ArUco's fast detector: over 1000 fps on 4K without parallelization (desktop CPU), so marker detection is far cheaper than CNN inference. — [Romero-Ramirez et al. 2018](https://burjcdigital.urjc.es/handle/10115/42233) [S]
- AprilTag detection is CPU-bound; Raspberry Pi 4/5 is common in FRC. — [LearnFRC/PhotonVision](https://learnfrc.com/blog/frc-photonvision-setup) [S, grey literature]
- Ultralytics documents exporting YOLO to OpenVINO for Intel CPUs (a deployment route, not a localization paper). — [Ultralytics robotics page](https://www.ultralytics.com/solutions/computer-vision-in-robotics) [S]
- A low-cost AMR study reports CPU usage for YOLOv2-Tiny through YOLOv7 on-robot (YOLOv7 averages about 87.5% CPU), but it is onboard rather than overhead. — [ResearchGate](https://www.researchgate.net/publication/383497693_YOLO_object_detection_and_classification_using_low-cost_mobile_robot) [S]

### Inferences
- The new system can contribute a **measured CPU-only latency/FPS** for YOLO (e.g. YOLOv8n/YOLO11n exported to ONNX or OpenVINO on a laptop CPU) in the closed loop, alongside localization error. No prior overhead-robot paper found reports this combination.
- ArUco on CPU at 30 fps is effectively free computationally. The YOLO system's cost should be justified by robustness or marker-free operation, not speed.

### Gaps
- I found no peer-reviewed benchmark of YOLO-OBB or YOLO-pose FPS on a Raspberry Pi or laptop CPU for robot tracking. Ultralytics benchmark pages exist but were not fetched.

---

## Q4. Works using homography / floor-plane calibration to map pixels to floor coordinates, and their accuracy

### Takeaway
Homography (image plane to floor plane) is the standard approach for fixed cameras and ground robots. A classic surveillance-camera study reports about **2.6 cm average and 7.1 cm maximum** error after homography-based compensation. Fiducial testbeds instead use fixed calibration tags (Duckietown) or a calibrated camera at known height (CPM Lab). Some recent markerless work (Robinson 2023) skips calibration entirely and controls in image space.

### Cited Findings
- Shim & Cho (earlier work, 2016), "A Mobile Robot Localization via Indoor Fixed Remote Surveillance Cameras," *Sensors* 16(2):195, 2016. The DOI 10.3390/s16020195 is inferred from the MDPI URL pattern [U], and the first names of Shim and Cho were not verified. Fixed ceiling/surveillance cameras with a homography from image planes to a 2D floor map give, after homography-based error compensation, **maximum 7.1 cm and average 2.6 cm** position error. Bultmann et al. 2023 also cite it as "Shim and Cho." — [MDPI](https://www.mdpi.com/1424-8220/16/2/195); [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4801572/) [S]
- Duckietown: fixed AprilTags on the road layer give each Watchtower's camera-to-map transform. — [arXiv 2305.09848](https://arxiv.org/pdf/2305.09848) [S]
- GroundGazer: undistortion plus a warp to a top-down view (an onboard camera, but the same homography idea) reaches sub-mm. — [arXiv 2509.17346](https://arxiv.org/html/2509.17346v1) [V]
- Robinson et al. 2023: "No camera calibration or intrinsics are needed"; the controller works in image space, with waypoints recorded as image coordinates. Cross-track error is at most about 10 cm (Office 1) and about 5 cm (Workshop), measured with a Leica tracker. — [arXiv HTML 2306.14848](https://arxiv.org/html/2306.14848) [V]
- A calibrated fixed camera loses validity if it is disturbed, and the "delicate procedure must be repeated" (manipulator context). — [arXiv 2008.11822](https://arxiv.org/pdf/2008.11822) [S]
- Robotarium: the camera needed recalibration through the day because of lighting (photometric thresholds rather than geometric calibration, but still a calibration-maintenance burden). — [Robotarium IEEE AAM](https://ieeexplore.ieee.org/ielaam/9552933/9973428/9996578-aam.pdf) [S]

### Inferences
- With a 4-point floor homography and a small robot, error comes mostly from (a) detector keypoint jitter in pixels times the metres-per-pixel scale and (b) parallax, because the detected point is at the robot's top surface rather than on the floor plane. The paper should correct for robot height, for example by computing the homography at robot-top height. This is my inference; I did not find a source that quantifies the parallax effect for overhead robot tracking.
- Reporting error in cm after homography (with a ground-truth grid or ArUco reference) would put the new system directly next to Shim & Cho (2.6 cm average) and HeRoSwarm/CPM (about 1 cm).

### Gaps
- I found no recent (2020+) paper that reports homography-only accuracy for a deep-learning detector of a ground robot.

---

## Q5. Works combining an overhead/external camera with closed-loop navigation to a target (eye-to-hand visual servoing of mobile robots)

### Takeaway
Yes. A control-theory line of work (2014-2020, plus earlier seminal papers) does image-based visual servoing (IBVS) of wheeled robots with an uncalibrated fixed ceiling camera, usually tracking one or a few feature points (often LEDs or markers). Robinson et al. (IROS 2023) is the clearest **learning-based** closed-loop example (YOLOv5 + orientation CNN + PD control), and testbeds (Robotarium, CPM Lab, Duckietown, HeRoSwarm) close the loop routinely with marker or LED tracking.

### Cited Findings
- "Adaptive Image-Based Trajectory Tracking Control of Wheeled Mobile Robots With an Uncalibrated Fixed Camera," IEEE, 2015 (IEEE document 7065229; the venue is probably IEEE Trans. Control Systems Technology [U]). A ceiling camera and a feature point on the robot's forward axis; the adaptive controller does not need intrinsic or extrinsic parameters or the feature position, and the camera need not be parallel to the floor. Validated in simulation and on a real robot. — [IEEE Xplore 7065229](https://ieeexplore.ieee.org/document/7065229/) [S; authors U]
- "Adaptive image-based visual servoing of wheeled mobile robots with fixed camera configuration," IEEE (document 6907773, ~2014, probably ICRA 2014 [U]). Ceiling camera with a depth-independent interaction matrix; Lyapunov convergence of image errors; simulation and experiments. — [IEEE Xplore 6907773](https://ieeexplore.ieee.org/document/6907773/) [S]
- Wang et al., "Adaptive Visually Servoed Tracking Control for Wheeled Mobile Robot with Uncertain Model Parameters in Complex Environment," *Complexity* 2020, **DOI 10.1155/2020/8836468** (from the Wiley URL). Kinematic and dynamic uncalibrated visual servoing with a ceiling camera. — [Wiley](https://onlinelibrary.wiley.com/doi/10.1155/2020/8836468) [S]
- Liang et al.?, "Simultaneous tracking and regulation visual servoing of wheeled mobile robots with uncalibrated extrinsic parameters," *Int. J. Systems Science* 49:217 (2018). — [ADS](https://ui.adsabs.harvard.edu/abs/2018IJSyS..49..217L/abstract) [S; authors U; check whether the camera is fixed or onboard]
- Earlier seminal work (pre-2018): "Visual servo tracking control of a wheeled mobile robot with a monocular fixed camera" (eye-to-hand; desired trajectory from a prerecorded image sequence of 4 target points). — [Academia.edu](https://www.academia.edu/2805022/Visual_servo_tracking_control_of_a_wheeled_mobile_robot_with_a_monocular_fixed_camera) [S; authors, year and venue U, probably Chen, Dawson et al., ~2004]
- Robinson et al. 2023 (IROS): a fully autonomous pipeline where a PD controller acts on cross-track and heading error relative to an image-space path, with rotate-in-place. Over 8 runs per location, the maximum cross-track error was about 10 cm (Office 1) and about 5 cm (Workshop). — [arXiv HTML 2306.14848](https://arxiv.org/html/2306.14848) [V]
- Bultmann et al. 2023: external camera poses are fused into the robot's navigation, and long-trajectory success rose from 1/5 to 5/5. — [ar5iv 2303.03797](https://ar5iv.labs.arxiv.org/html/2303.03797) [V]
- Testbeds close the loop with overhead tracking: the Robotarium (ArUco at up to 30 Hz, later Vicon) [S], CPM Lab (LEDs at 50 Hz) [S] and HeRoSwarm (AprilTag) [S]. Links are under Q1.

### Inferences
- The positioning gap is the **combination**: a markerless YOLO-family detector (with heading from OBB or keypoints), a floor homography to metric (x, y, θ), CPU-only real-time inference, and closed-loop go-to-target for a **holonomic omni** robot. Robinson 2023 is the nearest neighbour, but it uses a GPU, a differential-drive TurtleBot, an image-space controller with no metric calibration, and no marker comparison. Bultmann 2023 uses Jetsons, 4 cameras and a large service robot.
- Classic IBVS works give theoretical convergence guarantees but use simple point features (LEDs or markers). Citing them frames the new system as replacing hand-made features with learned detection.

### Gaps
- Authors and venues for IEEE 7065229 and 6907773 were not confirmed (the abstracts only).
- I found no work on external-camera closed-loop control of a **mecanum or omni-wheel** robot with learned detection. A targeted search ("mecanum robot overhead camera YOLO") could confirm this.
- Latency in the closed loop (camera to detection to command) is not reported by Robinson or Bultmann.
