# Closed-loop control of omni/mecanum robots with visual (overhead-camera) feedback, slip compensation, and low-cost camera-only systems

Scope: 4-wheel 45-degree omni (X-drive) and mecanum robots; external/overhead camera feedback vs encoder odometry; low-cost platforms (ESP32/Arduino/RPi). Target system: ESP32 + L298N + GM25-370 encoder motors + per-wheel PID, laptop-side go-to-goal from overhead webcam pose.

Verification notes (how citations were checked):
- Title, authors, venue, year and DOI were checked against the Crossref API (api.crossref.org/works/{DOI}) and/or OpenAlex (api.openalex.org) for the entries marked "[verified: Crossref/OpenAlex]". Abstract numbers marked "(abstract)" were read from the OpenAlex/Semantic Scholar abstract record.
- MDPI, PMC, Springer and ResearchGate full-text pages returned 403/captcha/login redirects, so full-text numbers (beyond abstracts) could not be read for most papers. Anything taken only from a search-engine snippet is marked "[snippet only - unverified]".
- HeRoSwarm numbers were read directly from the arXiv PDF full text.
- No DOIs were invented. Where no DOI was found, the URL is given.

## Q1. How large is encoder-odometry drift / wheel slip for omni and mecanum robots in reported experiments?

### Takeaway
Few papers report a clean "error per meter" for 4-wheel X-drive omni robots. Reported figures for comparable small robots are a few cm over 1-2 m paths (roughly 2-5% of distance traveled) for encoder-only odometry. The error grows quickly with speed and with heading changes, and heading error is the dominant failure mode. Even LIDAR-corrected omni path tracking leaves about 3-4 cm RMS and about 6-8 degrees RMS heading error at 0.3 m/s.

### Cited Findings
- **Palacín J., Rubies E., Clotet E., Martínez D. (2021).** "Evaluation of the Path-Tracking Accuracy of a Three-Wheeled Omnidirectional Mobile Robot Designed as a Personal Assistant." *Sensors* 21(21):7216. DOI 10.3390/s21217216 [verified: Crossref]. Platform: 3-wheel omni (APR-02 personal assistant). Sensing: onboard precise LIDAR for self-localization, with LIDAR scans registered to obtain the ground-truth trajectory. Control: path-tracking that corrects the trajectory. Results (abstract): at the nominal 0.3 m/s, RMS displacement error was 0.032 m on the circular path and 0.039 m on the eight-shaped path. Absolute maximum displacement errors were 0.077 m and 0.088 m. RMS orientation errors were 6.27° and 7.76°. Accuracy on the eight-shaped path worsens as velocity increases. — [MDPI](https://doi.org/10.3390/s21217216)
  - Search snippet: RMS distance error rose about one order of magnitude, from 0.017 m to 0.100 m, as velocity went from 0.1 to 0.5 m/s [snippet only - consistent with the abstract trend, but the exact figures were not seen in full text]. — [MDPI](https://doi.org/10.3390/s21217216)
- **HeRoSwarm, Starks M., Gupta A., Oruganti Venkata S.S., Parasuraman R. (2022).** "HeRoSwarm: Fully-Capable Miniature Swarm Robot Hardware Design With Open-Source ROS Support." arXiv:2211.03014 (the arXiv page names no peer-reviewed venue). Read from the full-text PDF:
  - An overhead AprilTag camera served as ground truth.
  - Encoder odometry (computed on an nRF52 Feather Sense) had a **mean absolute error of 6.3 cm (SD 4.1 cm) and a maximum of 12.8 cm** against the camera along a defined path, on a 2.5 x 1.75 m tabletop.
  - Max robot speed was 28 cm/s, and the mean velocity-tracking error was 4 cm/s.
  - Note: this is a small differential-drive-class swarm robot, not an omni robot. The drive type was not confirmed in the excerpt read. — [arXiv](https://arxiv.org/abs/2211.03014)
- **Fahmizal et al.** "Trajectory Tracking pada Robot Omni dengan Metode Odometry" (Indonesian). Rotary-encoder odometry on an omni robot gave an average error of about 1.75% in x and 4.71% in y on a square path, and below 5% on triangular paths [snippet only - year, venue and full author list unverified]. — [ResearchGate](https://www.researchgate.net/publication/334631115_Trajectory_Tracking_pada_Robot_Omni_dengan_Metode_Odometry)
- **"Calibration of omnidirectional wheeled mobile robots: Method and experiments"** (3-wheel omni, UMBmark-style). The paper names odometry error sources as unequal wheel diameters, joint misalignment, backlash and slippage. The proposed calibration reduced systematic error by a factor of 2.6 vs traditional UMBmark [snippet only - authors, venue and year not verified; likely pre-2018]. — [ResearchGate](https://www.researchgate.net/publication/259434997_Calibration_of_omnidirectional_wheeled_mobile_robots_Method_and_experiments)
- **Quan S., Chen J. (2021).** "Mecanum Wheeled Mobile Platform Odometry Error Analysis and Correction." In *Proceedings of IncoME-V & CEPE Net-2020*, Mechanisms and Machine Science, Springer, pp. 728-736. DOI 10.1007/978-3-030-75793-9_70 [verified: Crossref]. The abstract and numbers were not accessible (Springer login redirect). — [Springer](https://doi.org/10.1007/978-3-030-75793-9_70)
- **Alhalabi A., Ezim M., Canbek K.O., Baran E.A. (2020).** "A multiple sensor fusion based drift compensation algorithm for mecanum wheeled mobile robots." *Turkish Journal of Electrical Engineering & Computer Sciences*. DOI 10.3906/elk-2003-12 [verified: OpenAlex]. Platform: mecanum robot with high-precision wheel encoders and four chassis accelerometers. The inner disturbance-observer acceleration controller is "blind against the slipping motion of the wheels." Fusing encoders and accelerometers estimates drift acceleration, which is mapped back to joint space as compensation, and gives smaller tracking errors (abstract; no numbers in the abstract). — [DOI](https://doi.org/10.3906/elk-2003-12)
- **Yu X., Wang Z., Duan H., Yang X. (2026).** "Design and Experimental Validation of a Passive Following System for a Mecanum-Wheel Mobile Platform Based on Gimbal Posture Perception and Orthogonal Odometry Fusion." *Applied Sciences*. DOI 10.3390/app16136827 [verified: OpenAlex]. They explicitly address "pose errors caused by Mecanum-wheel slip and discontinuous roller-ground contact" by using two orthogonal passive (unpowered) odometry wheels plus IMU attitude. Platform: a 300 x 300 mm chassis, Infineon TRAVEO controller, DRV8701E drivers, magnetic encoders. Numbers are not in the abstract excerpt. — [DOI](https://doi.org/10.3390/app16136827)
- **Ortega-Lomeli L.D., Básaca-Preciado L.C., Orozco-Rosas U., Castro-Toscano J.D., Ponce-Camacho M.A. (2026).** "Eight-Wheel Mecanum Omnidirectional Autonomous Mobile Robot: Kinematics, Architecture, and Validation." *Electronics* 15(11):2441. DOI 10.3390/electronics15112441 [verified: Crossref]. Platform: ESP32-based wheel interfaces via micro-ROS, ROS 2, LiDAR, stereo, IMU, encoders. Results over 100 out-and-back campus missions (abstract):
  - 91/100 missions completed without safety interruptions.
  - Success rate was 96% outbound and 81% return, under the criteria e_p < 1.5 m and |e_θ| < 15°.
  - Final-pose medians after return were 1.016 m, 0.573 m and 28.5°.
  - The authors identify **heading recovery** as the main limitation. — [DOI](https://doi.org/10.3390/electronics15112441)
- Industry/hobby guide (not peer-reviewed): slip is the "design point" of mecanum wheels, so drivetrain-encoder-only localization accumulates error rapidly. FTC-style robots use unpowered "dead wheels" plus an IMU in an EKF. — [industrialmonitordirect guide](https://industrialmonitordirect.com/blogs/knowledgebase/mecanum-drive-base-odometry-and-path-planning-technical-guide)
- Vendor blog rule of thumb (not peer-reviewed): about 1-3% of distance (±1-3 cm/m) for a well-calibrated encoder robot. — [Zbotic](https://zbotic.in/encoder-wheel-odometry-robot-distance-position-arduino/)

### Inferences
- For a GM25-370 X-drive on a typical floor, plan for at least several cm of drift per meter, and significantly more under rotation or acceleration. Roller slip and floor contact affect X-drive/mecanum more than differential drive. This supports closing the outer loop on overhead-camera pose rather than on encoder odometry.
- Heading drift is the most damaging error, as Ortega-Lomeli 2026 and Palacín 2021 both show. An overhead camera that measures heading directly (e.g., ArUco/AprilTag orientation) removes the most harmful error term. An IMU gyro is a cheap secondary source.
- Unpowered tracking wheels (Yu 2026; FTC "dead wheels") are a hardware alternative to vision for slip observability.

### Gaps
- No peer-reviewed 2018-2026 paper found that reports encoder-only drift in mm/m or % for a **4-wheel 45° X-drive** specifically. Most omni data is 3-wheel (kiwi) or mecanum.
- The Quan & Chen 2021 numbers could not be read (paywall).
- No paper found that directly quantifies the slip ratio of omni rollers on common floors (tile/wood/carpet) for small DC gear motors.

## Q2. What methods fuse external camera or visual measurements with wheel odometry for omni/mecanum robots, and what accuracy gains are reported?

### Takeaway
The common pattern is an EKF (or complementary filter) with wheel odometry, and often a gyro, as the prediction step. Absolute measurements from an external positioning system (ultrasound IPS, camera, UWB) are used as corrections. Most low-cost papers report "significant improvement" qualitatively, and hard before/after numbers for omni robots are scarce. An overhead camera alone (no fusion) typically gives about 1 cm absolute accuracy, which is already better than encoder odometry after 1-2 m.

### Cited Findings
- **Nugraha M.H., Abdul F., Bramantyo L., Rijanto E., Saputra R.P., Mahendra O. (2024).** "Mobile Robot Localization via Indoor Positioning System and Odometry Fusion." 2024 IEEE Int. Conf. on Smart Mechatronics (ICSMech); arXiv:2509.22693. An EKF fuses an ultrasound IPS with wheel odometry. The abstract says fusion "significantly enhances accuracy and precision compared to standalone systems" and reduces "errors associated with wheel slippage and sensor noise." No numbers are in the abstract, and the platform wheel type is not stated in the abstract. — [arXiv](https://arxiv.org/abs/2509.22693)
- **Nguyen T.T., Le Q.-T., Pham Q.-P., Le T.-L. (2026).** "Research on Fuzzy-PID Control System for Mecanum Robot." *Journal of Automation, Mobile Robotics & Intelligent Systems (JAMRIS)*. DOI 10.14313/jamris-2026-039 [verified: OpenAlex]. Four-mecanum-wheel robot. An **IMU and a camera are fused with a complementary filter** for localization and heading. A fuzzy controller handles orientation and a fuzzy-PID handles position. They report "low RMS errors under a range of loading scenarios" on a real prototype (values not in the abstract). This is the closest published match to camera + IMU + mecanum with simple fusion. — [DOI](https://doi.org/10.14313/jamris-2026-039)
- **Saenz A., Santibañez V., Bugarin E., Dzul A., Ríos H., Villalobos-Chin J. (2020/2021).** "Velocity Control of an Omnidirectional Wheeled Mobile Robot Using Computed Voltage Control with Visual Feedback: Experimental Results." *International Journal of Control, Automation and Systems* 19:1089-1102. DOI 10.1007/s12555-019-1057-6 [verified: Crossref; online Dec 2020]. Position and velocity come from a multi-camera vision system, so motor-encoder measurements are not needed (from search snippet). Numbers were not accessible. — [Springer](https://doi.org/10.1007/s12555-019-1057-6)
- **Kao S.-T., Ho M.-T. (2021).** "Ball-Catching System Using Image Processing and an Omni-Directional Wheeled Mobile Robot." *Sensors* 21(9):3208. DOI 10.3390/s21093208 [verified: Crossref/Europe PMC]. The omni robot was **navigated through a static (external) camera**. A Kalman filter (with deep learning) reduces visual measurement noise. The controller is feedback linearization plus PID. The system was verified experimentally to "precisely catch a thrown ball" (abstract; numbers not read). — [DOI](https://doi.org/10.3390/s21093208)
- **Reginald N., Al-Buraiki O., Choopojcharoen T., Fidan B., Hashemi E. (2025).** "Visual-Inertial-Wheel Odometry with Slip Compensation and Dynamic Feature Elimination." *Sensors* 25(5):1537. DOI 10.3390/s25051537 [verified: Crossref]. Wheel-slip error is modeled with GPR (deep kernel + LSTM) inside an MSCKF. The paper claims significantly better localization than conventional VIWO. It uses onboard cameras and datasets, not an external camera, and it is not omni-specific. — [DOI](https://doi.org/10.3390/s25051537)
- **HeRoSwarm (Starks et al., 2022).** The overhead AprilTag camera server had an average position error of **0.8 cm**, measured on marked points, vs encoder odometry MAE of 6.3 cm on the same tabletop. The authors list odometry+IMU fusion as future work. — [arXiv](https://arxiv.org/abs/2211.03014)
- Older baseline (pre-2018): "Visual Odometry and Control for an Omnidirectional Mobile Robot with a Downward-Facing Camera" (IROS 2010, Deyle et al.). A downward camera does optical-flow odometry on a 4-wheel mecanum/omni base to compensate slip, with an overhead-calibrated camera as ground truth [authors and year from the PDF URL path; numbers not read]. — [PDF](https://www.deyle.com/publications/pdf/2010_iros_visualodom.pdf)
- Patent reference: a cleaning robot with a downward camera feeding an EKF for a slip-compensated local pose (US patent 12038756; details not read). — [USPTO](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12038756)
- Open-source practitioner findings (GitHub, not peer-reviewed):
  - An EKF over wheels alone just tracks raw odometry, and the gains come from adding a gyro.
  - Outlier gating handles spikes but not sustained slip.
  - Sources: [diffbot_ekf_sensor_fusion](https://github.com/ngnagomi/diffbot_ekf_sensor_fusion); [mecanum-ekf-localization](https://github.com/ca90m/mecanum-ekf-localization).

### Inferences
- For the target system, the simplest robust design has two layers. Per-wheel PID on the ESP32 gives the inner velocity loop. On the laptop, an outer loop runs on fused pose: a complementary filter or EKF uses commanded/encoder body velocity (from inverse X-drive kinematics) for prediction, and overhead-camera (x, y, θ) for correction.
- Because the camera has about 1 cm absolute accuracy and no drift, the filter mainly serves two purposes: bridging frames and latency, and riding through marker dropouts. Encoder odometry only needs to be good over about 100 ms horizons.
- A gyro (e.g., an MPU6050 on the ESP32) is the cheapest high-value addition. Heading is what slip corrupts most, and camera heading is noisier than position when the marker is small.

### Gaps
- No 2018-2026 paper found with a quantitative "encoder-only vs encoder+overhead-camera EKF" comparison on a 4-wheel omni/mecanum robot. The JAMRIS 2026 and ICSMech 2024 numbers were not accessible.
- The Saenz et al. 2020 vision rate, latency and accuracy figures were not accessible.

## Q3. What go-to-goal / point-stabilization / trajectory-tracking controllers are used for holonomic robots, and what final position accuracy is typical?

### Takeaway
Most practical holonomic work uses PID or fuzzy-PID in world frame, rotated into body frame, with inverse kinematics to wheel speeds. More advanced options are feedback linearization + PID, computed-voltage/dynamic control, MPC, and position-based visual servoing (PBVS). Typical reported accuracies:

| Setup | Typical accuracy |
|---|---|
| Lab path tracking | about 2-4 cm RMS, about 6-8° heading |
| Overhead-camera position control on low-cost omni robots | several cm |
| Campus-scale mecanum with LiDAR/IMU | tens of cm to about 1 m |

### Cited Findings
- **Palacín et al. 2021** (3-wheel omni, LIDAR-based path tracking): 3.2-3.9 cm RMS and 7.7-8.8 cm max at 0.3 m/s, with 6.27-7.76° RMS heading. — [DOI](https://doi.org/10.3390/s21217216)
- **Sukamta S., Nugroho A., Subiyanto S., Rezianto R., Soambaton M.F. (2024).** "Image-Based Position Control for Three-Wheel Omni-Directional Robot." *Jurnal Ilmiah Teknik Elektro Komputer dan Informatika (JITEKI)* 10(3). DOI 10.26555/jiteki.v10i3.29601 [verified: OpenAlex]. Low-cost analogue of the target system:
  - Sensing: an **infrared camera mounted on the ceiling** detects the robot position, and image processing defines waypoints.
  - Test area: "X" and "Square" trajectories in a 1.8 x 1.8 m room.
  - Results: "X" trajectory MAE per segment 52.49-134.96, average 91.36. "Square" average 83.17.
  - Units are not stated in the abstract and are likely pixels or mm, so treat them as unverified units.
  - Claims improved accuracy vs conventional methods. — [DOI](https://doi.org/10.26555/jiteki.v10i3.29601)
- **Kao & Ho 2021**: feedback linearization + PID for an omni robot guided by a static camera. — [DOI](https://doi.org/10.3390/s21093208)
- **Nguyen et al. 2026 (JAMRIS)**: fuzzy (orientation) + fuzzy-PID (position) for a 4-mecanum robot with camera+IMU feedback. — [DOI](https://doi.org/10.14313/jamris-2026-039)
- **Zhang Z., Wang Z., Zhang X. (2026).** "Kinematics and Comparative Evaluation of a Novel Decoupled, Redundantly-Actuated Four-Wheeled Omnidirectional Mobile Robot with Trajectory Tracking Validation." *Results in Engineering*. DOI 10.1016/j.rineng.2026.112281 [verified: OpenAlex]. Uses two orthogonal pairs of omni wheels (not 45° X), with PID trajectory tracking of parabolic, spline, line+rotation and Bezier curves, in simulation and experiment. The feasible region is 53.96% larger than a 3-wheel robot. — [DOI](https://doi.org/10.1016/j.rineng.2026.112281)
- **Roșca R.-L., Iancu A.-I., Burlacu A., Dosoftei C. (2026).** "Integrating Visual Perception and Control Strategies in Custom Omnidirectional Mobile Robots." *Sensors* 26(12):3918. DOI 10.3390/s26123918 [verified: Crossref]. Onboard stereo camera, ROS. Compares classic PBVS (quaternion pose error) with a Dual-Lie-algebra pose-free law for docking. Both achieve docking, and the dual approach gives more robust movement (abstract; numeric errors not read). — [DOI](https://doi.org/10.3390/s26123918)
- MPC for mecanum trajectory tracking (conference papers, numbers not read):
  - Li Y. et al. (2023). "Adaptive model predictive control for trajectory tracking of Mecanum mobile robots." ICCEA 2023. DOI 10.1109/iccea58433.2023.10135332 [verified: Crossref]. — [DOI](https://doi.org/10.1109/iccea58433.2023.10135332)
  - Ji W. et al. (2022). "Application of Model Predictive Control to Trajectory Tracking of Mecanum Wheels." IEEE ICETCI 2022. DOI 10.1109/icetci55101.2022.9832159 [verified: Crossref]. — [DOI](https://doi.org/10.1109/icetci55101.2022.9832159)
- Visual-servoing omni path following (2017): Safia F., Fatima C. "Visual path following by an omnidirectional mobile robot using 2d visual servoing." ICEE-B 2017. DOI 10.1109/icee-b.2017.8192097 [verified: Crossref; numbers not read]. — [DOI](https://doi.org/10.1109/icee-b.2017.8192097)
- **Ortega-Lomeli et al. 2026**: large-scale mecanum navigation. Median intermediate-waypoint errors were 0.64 m, 0.191 m and 17°, which shows that without an absolute reference, accuracy degrades to decimeter-meter level. — [DOI](https://doi.org/10.3390/electronics15112441)
- **Shafiq M.U. et al. (2024).** "Real-time navigation of mecanum wheel-based mobile robot in a dynamic environment." *Heliyon*. DOI 10.1016/j.heliyon.2024.e26829 [verified: OpenAlex]. Uses hybrid A* + velocity obstacles on a mecanum robot, evaluated qualitatively. — [DOI](https://doi.org/10.1016/j.heliyon.2024.e26829)

### Inferences
- For a holonomic X-drive, go-to-goal reduces to three decoupled loops in world frame (e_x, e_y, e_θ), each a P/PI with saturation, then rotation by -θ into body frame and X-drive inverse kinematics. The literature (Kao & Ho; Nguyen 2026; Zhang 2026) shows PID-family controllers are sufficient. MPC adds value mainly for speed and acceleration constraints.
- With about 1 cm camera accuracy, a realistic final-position target is 1-3 cm and 2-5° when a stopping tolerance/deadband is used. This is an inference from HeRoSwarm's 0.8 cm camera error plus actuator deadband, and is not directly measured in a cited omni paper.

### Gaps
- No 2018-2026 paper found that reports final point-stabilization error for a 4-wheel 45° X-drive under overhead-webcam feedback.
- The MPC paper numbers (RMSE) were not accessible.

## Q4. What low-cost, camera-only robot platforms or testbeds exist, with costs and accuracies?

### Takeaway
Overhead-camera tracking with fiducial tags (AprilTag/ArUco) is the standard low-cost alternative to Vicon/OptiTrack in swarm and educational testbeds. It gives sub-cm to about 1 cm accuracy on tabletop arenas with robots costing about $100 or less. Motion-capture systems reach sub-mm accuracy but cost far more.

### Cited Findings
- **HeRoSwarm (Starks et al., arXiv 2022)**:
  - COTS design with a **total cost of $100 per robot**, size 7 x 7.3 x 5.3 cm, Raspberry Pi Zero + nRF52 (Adafruit Feather Sense), ROS.
  - Overhead camera with AprilTags (three axis tags define the frame) on a 2.5 x 1.75 m tabletop gives a **0.8 cm average error**.
  - Compares itself to Georgia Tech's GRITSBot.
  - Source: PDF full text. — [arXiv](https://arxiv.org/abs/2211.03014)
- **Reina A., Cope A.J., Nikolaidis E., Marshall J.A.R., Sabo C. (2017).** "ARK: Augmented Reality for Kilobots." *IEEE Robotics and Automation Letters*. DOI 10.1109/lra.2017.2700059 [verified: Crossref]. Integrated **overhead tracking and control** of hundreds of Kilobots, open source, "inexpensive, off-the-shelf hardware" (abstract). A follow-up is Feola et al. 2023, RA-L, DOI 10.1109/lra.2023.3312031 [verified: Crossref]. — [DOI](https://doi.org/10.1109/lra.2017.2700059)
- **Wilson S., Glotfelter P., Wang L., Mayya S., Notomista G., Mote M., et al. (2020).** "The Robotarium: Globally Impactful Opportunities, Challenges, and Lessons Learned in Remote-Access, Distributed Control of Multirobot Systems." *IEEE Control Systems Magazine*, Feb 2020. DOI 10.1109/mcs.2019.2949973 [verified: Crossref]. A remote-access testbed with GRITSBots and overhead motion tracking. Its tracking hardware details and cost were not read here. — [DOI](https://doi.org/10.1109/mcs.2019.2949973)
- **Arvin F., Espinosa J., Bird B., West A., Watson S., Lennox B. (2018).** "Mona: an Affordable Open-Source Mobile Robot for Education and Research." *Journal of Intelligent & Robotic Systems*. DOI 10.1007/s10846-018-0866-9 [verified: Crossref]. A low-cost open-hardware robot (University of Manchester). The exact cost is not in the abstract. — [DOI](https://doi.org/10.1007/s10846-018-0866-9)
- **Survey (arXiv 2408.14199)**: "A Survey on Small-Scale Testbeds for Connected and Automated Vehicles and Robot Swarms."
  - Vicon-based testbeds are below 1 mm, and an OptiTrack minicar testbed is below 0.2 mm.
  - The CPM Lab camera-based global positioning is less precise than Vicon/OptiTrack but acceptable at much lower cost.
  - [snippet only - figures from search summary, full text not read]. — [arXiv](https://arxiv.org/abs/2408.14199)
- **DOTS: An Open Testbed for Industrial Swarm Robotic Solutions**: ArUco markermaps seen by multiple low-cost cameras for localization, computationally lighter than visual SLAM [snippet only - authors/venue not verified]. — [ResearchGate](https://www.researchgate.net/publication/359506025_DOTS_An_Open_Testbed_for_Industrial_Swarm_Robotic_Solutions)
- **ESP32-CAM for ArUco (IMAV 2024, "Comparative Analysis of Cameras for ArUco Marker...")**: the ESP32 camera is cheaper, lighter and lower-power, but had a lower ArUco detection rate than other cameras tested, especially in low light [snippet only]. — [IMAV PDF](https://www.imavs.org/papers/2024/21.pdf)
- "Investigation of ArUco Marker Placement for Planar Indoor Localization" (arXiv 2509.17345) studies how marker placement affects planar localization accuracy [title only; numbers not read]. — [arXiv](https://arxiv.org/abs/2509.17345)
- "Development of a low-cost ground robot for real-time ArUco marker localization using lightweight deep learning models on an edge device" (ScienceDirect 2026, S277237552600122X) [title only; details not read]. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S277237552600122X)
- Older overhead-camera omni reference (2008, SciTePress, "Dynamical models for omni-directional robots with 3 and 4 wheels"): overhead camera at about 25 fps with about 1 cm position accuracy, used for model identification [snippet only; pre-2018]. — [PDF](https://www.scitepress.org/papers/2008/14892/14892.pdf)
- **Sukamta et al. 2024 (JITEKI)**: a ceiling IR camera with a 3-wheel omni in a 1.8 x 1.8 m room is a direct low-cost analogue. Cost is not stated in the abstract. — [DOI](https://doi.org/10.26555/jiteki.v10i3.29601)

### Inferences
- A single USB webcam (720p/1080p, about 30 fps) looking down at a 1-2 m arena with a 5-10 cm ArUco/AprilTag on the robot is in line with published low-cost testbeds. Expect about 0.5-1 cm position accuracy after camera calibration and a planar homography, based on HeRoSwarm's 0.8 cm. Lens distortion calibration and marker-height (parallax) correction matter.
- Use the laptop webcam/USB webcam rather than an ESP32-CAM for tracking, given the ESP32-CAM detection-rate issues.

### Gaps
- Exact costs for the Robotarium tracking system, DOTS and Mona were not retrieved.
- No published bill of materials was found for an ESP32 + L298N omni robot with overhead webcam tracking (only hobby projects).

## Q5. What latency in the vision loop is tolerable for such control, and how do works handle it?

### Takeaway
Direct evidence for small omni robots is thin. Reported low-cost wireless ESP32 pipelines achieve about 50 ms control latency and 20-25 fps video. Overhead-camera testbeds run at about 25-30 fps (33-40 ms per frame). End-to-end camera-to-actuation delays of about 60-150 ms are typical. Works handle delay with a Kalman filter or prediction (estimating position and velocity, predicting forward), an inner fast loop on encoders, and conservative outer-loop gains and speeds.

### Cited Findings
- **Khan U.A., Ilyas A., Khan E. (2026).** "Advanced Frameworks for Low-latency Teleoperation and LLM-driven Autonomous Exploration in Omnidirectional Mobile Robotics." DOI 10.64589/juri/231349 [verified: OpenAlex; journal name not resolved by OpenAlex]. Platform: a 4-wheel-drive **mecanum robot with two ESP32-S3 nodes**, one for control and one for QVGA video streaming. Measured **about 50 ms control latency** and 20-25 fps FPV video (abstract). The robot was teleoperated, not autonomous visual closed-loop control. — [DOI](https://doi.org/10.64589/juri/231349)
- **Kao & Ho 2021**: a Kalman filter on the visual measurements estimates position and velocity and predicts the future trajectory. Prediction is how they handle vision delay and noise (abstract). — [DOI](https://doi.org/10.3390/s21093208)
- **HeRoSwarm**: the overhead camera server publishes robot poses to ROS topics, and the camera is used as ground truth/state for all robots. The latency figure was not found in the excerpt read. — [arXiv](https://arxiv.org/abs/2211.03014)
- **Altafi H., Shakeel R., Zareinia K. (2026).** Research Square preprint, DOI 10.21203/rs.3.rs-10604918/v1 [verified: OpenAlex]. A camera-to-display pipeline breakdown measured a network delay of 5.59 ± 1.04 ms vs a total camera-to-display delay of 77.95 ± 10.17 ms. Most latency comes from processing and display stages, not the network. This is a teleoperation context, not robot control. — [DOI](https://doi.org/10.21203/rs.3.rs-10604918/v1)
- **Tahir N., Parasuraman R. (2022).** "Analog Twin Framework for Human and AI Supervisory Control and Teleoperation of Robots." *IEEE Trans. SMC: Systems*. DOI 10.1109/tsmc.2022.3216206 [verified: OpenAlex]. Analyzes network delay vs tracking error and goal-reach accuracy for remotely controlled mobile robots (numbers not read). — [DOI](https://doi.org/10.1109/tsmc.2022.3216206)
- Overhead camera at about 25 fps in a 2008 omni model-identification setup [snippet only, pre-2018]. — [PDF](https://www.scitepress.org/papers/2008/14892/14892.pdf)

### Inferences (engineering reasoning, not from a single source)
- Rule of thumb: a delay τ in the position loop limits proportional gain to roughly Kp·τ < 0.3-0.5 (1/s · s) to avoid overshoot and oscillation. With τ ≈ 100 ms (webcam capture 33 ms + detection 10-20 ms + WiFi/UDP 5-20 ms + ESP32 PID period), the outer-loop Kp should be at most about 3-5 s⁻¹. That gives a time constant of about 0.2-0.3 s, which is fine for go-to-goal at 0.2-0.5 m/s.
- Recommended mitigations, consistent with Kao & Ho's KF-prediction approach:
  1. Timestamp frames and predict the pose forward by τ using commanded body velocity or encoder odometry.
  2. Keep the per-wheel PID on the ESP32 at 50-100 Hz, independent of camera rate.
  3. Slow down near the goal and use a deadband, with separate xy and θ tolerances.
  4. Run the camera pipeline on a fixed-exposure webcam (MJPG at 30 fps or more) to cut capture latency and motion blur.
- A watchdog is a safety necessity for any WiFi-commanded robot: the ESP32 stops if no command arrives within about 200-300 ms.

### Gaps
- No peer-reviewed 2018-2026 study found that measures tolerable vision-loop latency (stability margin vs delay) specifically for omni/mecanum go-to-goal with an overhead webcam.
- Saenz et al. 2020 (IJCAS) likely reports the vision sampling rate, but it was not accessible.
