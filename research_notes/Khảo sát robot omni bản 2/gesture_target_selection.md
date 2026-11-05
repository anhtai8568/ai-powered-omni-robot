# Hand-Gesture Interfaces for Mobile-Robot Target Selection (pointing, air-mouse, pinch-to-select, MediaPipe)

Scope note: positioning a system where a MediaPipe-Hands index-finger cursor moves over an overhead-camera floor view, a pinch selects a detected object, and an omni robot drives to it. The authors' v1 baseline: rule-based static gestures, about 260 ms from gesture to wheel. Verification legend: **[V]** = details checked on the arXiv, publisher, or author page; **[S]** = from a search snippet or secondary page only, so check before citing.

## Q1. Representative MediaPipe / RGB-hand-tracking robot teleoperation systems, and the latency and accuracy they report

### Takeaway
MediaPipe-based robot teleoperation is common, but most papers are small, simulation-only, or report no end-to-end latency. Reported figures run from about 20 ms (recognition only) to about 130 ms (gesture to action), and few papers measure all the way to the actuator. A properly measured end-to-end figure (gesture to wheel, about 260 ms in v1) is therefore a contribution in itself, provided the measurement boundaries are stated clearly.

### Cited Findings
- **MediaPipe Hands (base technology)** [V]: Zhang, Bazarevsky, Vakunov, Tkachenka, Sung, Chang, Grundmann (2020), "MediaPipe Hands: On-device Real-time Hand Tracking", CVPR Workshop on Computer Vision for AR/VR, arXiv:2006.10214. Two-stage pipeline: a palm detector, then a landmark model that outputs 21 landmarks (x, y, relative depth). The palm detector runs only when tracking is lost. Real time on mobile GPUs; single RGB camera. — [arXiv](https://arxiv.org/abs/2006.10214v1); [Google Research](https://research.google/pubs/mediapipe-hands-on-device-real-time-hand-tracking)
- **AutoNav, multi-robot teleoperation** [V partial]: Zick, Martinelli, Schneider de Oliveira, Kalempa (2024), "Teleoperation system for multiple robots with intuitive hand recognition interface", *Scientific Reports* 14:30230, DOI 10.1038/s41598-024-80898-x. The palm-based interface uses MediaPipe and a USB camera. ROS, with multiple TurtleBot3 robots in Gazebo/RViz (simulation only). The hand's position in the camera image is mapped to map coordinates (shown in RViz). A robot marker follows the hand once the hand goes from open to closed, which is a "grab-and-place goal" metaphor close to pinch-to-select. Results: execution time reduced by about 50%, operator free time up to 94% of execution time, and fewer collisions. Latency and user-study size were not retrievable (the PMC page was blocked). — [DOAJ](https://doaj.org/article/3c722e7ea7d448d7aceef2e7b3da3c0b); [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11618356/); [search summary](https://www.nature.com/articles/s41598-024-80898-x)
- **Vision-based gesture tracking for mobile manipulators** [V]: T. Wang, Y. Wan, C. Peers, J. Sun, C. Zhou (2022), UKRAS22 Proceedings, pp. 52–53, DOI 10.31256/Bj3Qo8Y. MediaPipe hand coordinates plus gestures teleoperate a Husky with an arm in PyBullet simulation. The 2-page abstract gives no quantitative latency or accuracy. — [White Rose](https://eprints.whiterose.ac.uk/id/eprint/189808/)
- **Tracked robot with MediaPipe** [V metadata / S numbers]: Wameed, Alkamachi, Erçelebi (2023), "Tracked Robot Control with Hand Gesture Based on MediaPipe", *Al-Khwarizmi Engineering Journal* 19(3):56–71, DOI 10.22153/kej.2023.04.004. Classifies gestures from 21 landmarks and maps each gesture to a robot motion. The abstract says accuracy and response time degrade with distance, light intensity and hand tilt. A search snippet (ResearchGate/Academia) reports a 0.133 s average gesture-to-action response time and 100% accuracy at 1 m; this was not confirmed on the journal page. — [journal](https://alkej.uobaghdad.edu.iq/index.php/alkej/article/view/843); [ResearchGate](https://www.researchgate.net/publication/381110836_Tracked_Robot_Control_with_Hand_Gesture_Based_on_MediaPipe)
- **Robot dog, senior-robot interaction** [S]: arXiv 2512.17136 reports 22.0 ms hand-gesture latency in bright light and 84% (21/25) accuracy in dim light. Single operator, 25 trials. — [arXiv](https://arxiv.org/pdf/2512.17136)
- **Mobile manipulator, one-hand MediaPipe + LSTM** [S]: Jc-IFToMM Symposium 2024; the LSTM reached 100% on 3 gesture types. — [J-STAGE](https://www.jstage.jst.go.jp/article/jciftomm/7/0/7_178/_article/-char/en)
- **Non-peer-reviewed reference points** [S]: (a) an LSTM+MediaPipe robot-arm thesis repo claims 91.2% on 6 gestures and 61.4 ms latency on a laptop CPU. Its published code has a fixed `time.sleep(0.1)` inside the timed region, so the figure is unreliable. (b) A ROS 2 Raspberry Pi 5 hobby build reports 15 FPS at 640x480 and <100 ms detection-to-command. — [GitHub](https://github.com/Varaha18/lstm-gesture-recognition); [Hackaday](https://hackaday.io/project/203704-gesturebot-ros2-computer-vision-mobile-platform/log/242658-implementing-real-time-gesture-recognition-for-robot-control)
- **Long-range RGB gestures for a quadruped** [V]: Bamani, Nissinman, Meir, Koenigsberg, Sintov, "Ultra-Range Gesture Recognition using a Web-Camera in Human-Robot Interaction", arXiv:2311.15361 (v2, Apr 2024; no venue on the arXiv page). 6 classes (pointing, thumbs-up/down, beckoning, stop, null) at up to 25 m (demo at 28 m). YOLOv3 crop, then HQ-Net super-resolution, then a GViT (graph conv + ViT) classifier. 98.1% on the test set and about 96% in robot runs (98% outdoor, 97% indoor, 94% courtyard). Human observers averaged 78.4%. Unitree Go1 + Jetson Orin Nano; inference rate 11.43 Hz. No latency number given; the authors note visible delay from wireless offloading. — [arXiv](https://arxiv.org/html/2311.15361v2)

### Inferences
- Most MediaPipe-robot papers report per-frame recognition time (about 20–100 ms), not end-to-end gesture-to-actuator latency. The v1 figure of about 260 ms is not directly comparable to these. The paper should break latency into camera capture, inference, classification/debounce, network (WiFi), firmware and motor response, and compare each stage separately.
- Few systems in this group have a proper user study (N, SUS, TLX). Simulation-only validation (AutoNav, Leeds) is common, so a physical-robot user study would set v2 apart.

### Gaps
- No peer-reviewed MediaPipe mobile-robot paper found that reports end-to-end gesture-to-wheel latency measured with a high-speed camera or similar.
- AutoNav's latency and participant count could not be verified (PMC blocked). Wameed et al.'s numeric results are unverified.

## Q2. Pointing gestures for selecting a target object or location for a robot, and how accurate pointing-based selection is

### Takeaway
Deictic pointing from body or finger pose gives about 3–7 cm error on a tabletop and 1.4–2° angular error with dedicated models. Off-the-shelf pose or MediaPipe ray casting is much worse (about 17–28°). Mobile robots reach pointed ground targets with about 0.3 m error and 87–100% success. Visual feedback of the pointing ray significantly improves selection accuracy, which supports v2's design: a visible cursor on a camera view instead of free-space ray casting.

### Cited Findings
- **Kavousian, Petrovic, Herfs (2026)** [V, read full PDF]: "Intuitive Human-Robot Interaction: Development and Evaluation of a Gesture-Based User Interface for Object Selection", Proc. 72nd GfA Conference, Kassel (GfA-Press), pp. 202–207; arXiv:2604.06073. Intel RealSense D435i (RGB-D). Objects are segmented in the image, then selected by a pointing line (finger-based vs wrist-based). Selection is confirmed by a two-hand "click" gesture that fires when the second hand's fingertip distance falls below a threshold, which is pinch-like. The camera image and UI were shown on a screen. N=20, 2×2 within-subjects design (pointing line × visual feedback). Accuracy (mean, SD): Finger+feedback 93.3% (7.3); Wrist+feedback 91.5% (8.9); Finger without feedback 90.8% (8.1); Wrist without feedback 82.1% (17.6). Visual feedback had a significant main effect (p = 0.037). Selection time was about 3–4 s per trial in every condition. Errors came mostly from objects placed close together. Questionnaire: Likert understandability only, no SUS/TLX. Cites Quintero et al. 2013 (SEPO) object-selection success of only 51–69%. — [arXiv](https://arxiv.org/abs/2604.06073)
- **Sassali & Pieters (2025)** [V]: "Evaluating Pointing Gestures for Target Selection in Human-Robot Collaboration", IEEE RO-MAN 2025 (accepted), arXiv:2506.22116. RGB-D camera; OpenPose (OpenDR) 2D pose with a shoulder-wrist extension geometric model onto a planar workspace; Franka Panda arm; pointing integrated with object detection and speech. Mean localisation error 3.0–3.3 cm (dominant hand) vs 6.4–6.7 cm (non-dominant). Place-task success: 100% for a 20 cm area (both hands); 72.9% right / 56.7% left for 10 cm; 20.9% right / 8.0% left for 5 cm. Pick test 60–80% (right). The authors suggest about 6 cm as the minimum reliable target size. All tests were done by one right-handed person (no user study). — [arXiv HTML](https://arxiv.org/html/2506.22116)
- **Bamani et al. (2023/2025), PointingNet** [V]: "Real-time Human Finger Pointing Recognition and Estimation for Robot Directives Using a Single Web-Camera", arXiv:2307.02949; journal version listed as IEEE Access (2025), DOI 10.1109/ACCESS.2025.3616050 (taken from the arXiv page, journal page not opened). Single RGB webcam; classification plus regression of index-finger position and direction, with an arm-segmentation mask and MiDaS depth. Yaw 1.4 ± 1.3°, pitch 0.61 ± 0.63°, position RMSE 61.3 mm. Real-time session: 1.78° yaw, 0.8° pitch. The **MediaPipe index-finger baseline gives 26.1° yaw / 17.3° pitch error**, and general pose models about 28°. Navigation to the pointed target, 15 trials per robot: Unitree Go1 100% success, 0.36 ± 0.28 m error; Clearpath Husky 86.7%, 0.32 ± 0.20 m. Camera at 38 Hz. — [arXiv HTML](https://arxiv.org/html/2307.02949)
- **Gu, Croft, Cosgun (2022)** [V abstract]: "AR Point&Click: An Interface for Setting Robot Navigation Goals", ICSR 2022, arXiv:2203.15219. The AR headset's hand tracking detects pointing, then a **pinch confirms** the navigation goal, which the user can adjust. Compared against Person Following and a Tablet bird's-eye map interface. AR Point&Click improved perceived accuracy, efficiency and mental load over the tablet, and was on par with Person Following. N and numeric results were not on the abstract page. This is the closest prior work to "point + pinch to set a mobile-robot goal". — [arXiv](https://arxiv.org/abs/2203.15219)
- **Older reference points** [S]: SEPO, Quintero, Jagersand et al., ICRA 2013, pp. 1166–1171, a pointing-based selection interface with low spatial error up to 3 m — [ResearchGate](https://www.researchgate.net/publication/236053982_SEPO_Selecting_by_Pointing_as_an_Intuitive_Human-Robot_Command_Interface). Mobile-robot semantic-map pointing (arXiv 1710.08682): users point about 11° left and 9° above the target with the elbow-hand method, and the error depends on target location — [arXiv](https://arxiv.org/pdf/1710.08682). RGB-D pointing localisation (arXiv 2001.03687): 89.59% / 79.92% success on a 2×3 target matrix (left/right arm) — [arXiv](https://arxiv.org/pdf/2001.03687).

### Inferences
- Raw MediaPipe finger-ray pointing (about 17–26° error) is too inaccurate for selecting floor targets at room scale. This is a strong argument for v2's indirect "cursor on overhead camera view" approach: it turns a 3D deictic problem into a 2D relative-cursor problem with closed-loop visual feedback. The Kavousian et al. feedback effect (p = 0.037) supports this.
- v2 can report selection accuracy (% correct object), time per selection (Kavousian's about 3–4 s is a useful benchmark), and final robot-to-target position error (Bamani's about 0.3 m is a useful benchmark).

### Gaps
- AR Point&Click sample size and numeric outcomes were not retrieved (the full paper is needed).
- No pointing work found that uses an overhead or fixed camera of the floor with a desktop webcam for the hand, which is exactly v2's configuration. This looks like an open niche, but the search was not exhaustive.

## Q3. Mid-air cursor / air-mouse selection on a live camera view, compared with mouse/touch baselines

### Takeaway
No robotics paper was found that uses a webcam air-mouse cursor over a live camera view to command a robot with a mouse/touch baseline. The nearest robot analogues are click-on-image interfaces (mouse) and AR point-and-pinch. HCI literature consistently finds mid-air pointing reaches about 50–75% of mouse throughput, and pinch is fast but error-prone and fatiguing. v2 should therefore include a mouse-click baseline on the same camera view.

### Cited Findings
- **Dube, Ren, Limerick, MacKenzie, Arif (2022)** [V]: "Push, Tap, Dwell, and Pinch: Evaluation of Four Mid-air Selection Methods Augmented with Ultrasonic Haptic Feedback", *Proc. ACM HCI* 6(ISS), Art. 565, pp. 207–225, DOI 10.1145/3567718. Leap Motion plus an Ultraleap haptic board; N=12; ISO-style Fitts task, 1,296 observations. Throughput: Tap 2.29, **Pinch 2.21**, Push 1.92, Dwell 1.75 bps. Movement time: Tap 1490 ms, Pinch 1810 ms, Push 1749 ms; Dwell is reported as 19396 ms, which looks like a typo (likely about 1940 ms, unverified). Error rates: Pinch 1.99%, Tap 1.77%, Push 2.32%, Dwell 0%. Pinch was "fairly fast but error-prone and physically and cognitively demanding". Haptics improved throughput (1.96 to 2.09 bps). — [author page](http://www.yorku.ca/mack/iss2022.html)
- **Same line of work, gesture vs mouse** [S]: a mid-air gesture had 45% lower throughput than the mouse and 28% lower than the touchpad (2.6 vs 4.8 vs 3.7 bps, dominant hand). The search snippet attributed this to the same ISS 2022 paper set; the exact source is unconfirmed. — [yorku PDF](http://www.yorku.ca/mack/iss2022.pdf)
- **Brown, Stuerzlinger et al. (GI 2014)** [S]: "In-Air Un-Instrumented Pointing Performance". Throughput for markerless in-air pointing was below 75% of the mouse's; the authors argue latency, training and better finger tracking could close the gap. — [Graphics Interface](https://graphicsinterface.org/?p=5149); [York thesis](https://yorkspace.library.yorku.ca/bitstreams/b33d030f-68e1-45be-86de-894ab9ebf6d7/download)
- **Two-hand pinch point-and-click vs mouse, keyboard, TouchFree** [S]: ACM DOI 10.1145/3612783.3612810 (Interacción 2023, Univ. Navarra). LeapPointer was significantly faster than the other touchless technique (TouchFree) but less accurate. — [ACM DL](https://dl.acm.org/doi/10.1145/3612783.3612810)
- **WristPP (arXiv 2603.00606, 2026)** [S]: median selection time 861 ms for the mouse, 1574 ms for the touchpad and 2111 ms for the virtual air mouse; both alternatives were significantly slower than the mouse. — [arXiv](https://arxiv.org/pdf/2603.00606)
- **MediaPipe webcam virtual mouse** [S]: ICISD 2025 (Atlantis Press) reports 92.5% gesture accuracy and <150 ms latency, with no Fitts throughput or mouse baseline. — [Atlantis Press](https://www.atlantis-press.com/proceedings/icisd-25/126016972)
- **Camera Mouse benchmark** [S]: dwell-select Camera Mouse about 1.28 bps vs touchpad about 2.10 bps (Mack lab, HCII 2019). — [York HCII 2019](https://www.yorku.ca/mack/hcii2019.html)
- **Robot analogues:** AR Point&Click (pinch to confirm a goal, vs tablet map) — [arXiv](https://arxiv.org/abs/2203.15219). Mouse click-on-image task authoring for remote robots (arXiv 2109.02301) [S] — [arXiv](https://arxiv.org/pdf/2109.02301). AutoNav hand-position-to-map-goal mapping with open/close-to-grab — [DOAJ](https://doaj.org/article/3c722e7ea7d448d7aceef2e7b3da3c0b).

### Inferences
- Expect the v2 pinch cursor to be about 25–50% slower (lower throughput) than a mouse on the same overhead view. The justification should therefore rest on touchless or hands-free use, natural mapping, and the absence of extra hardware, not on raw speed. Pinch false triggers (the "Midas touch" problem) and arm fatigue (consider reporting Consumed Endurance or Borg CR10) are reviewer-expected discussion points.
- Useful design levers from the HCI work: hover feedback (haptic or visual) improves throughput; dwell is the most accurate but slow. A pinch hysteresis threshold and cursor smoothing (e.g., One-Euro filter) belong in the method section. One-Euro is not cited here; find a source if used.

### Gaps
- No direct "webcam MediaPipe air-mouse vs mouse vs touch on a robot camera view" study found. This is a likely novelty claim, but state it as "to our knowledge".
- The exact source of the 2.6/4.8/3.7 bps comparison is unconfirmed.

## Q4. Rule-based vs learned (MLP, LSTM, transformer on landmarks) gesture recognition for robot control, and typical accuracy

### Takeaway
Landmark-based learned classifiers typically report 90–100% accuracy on small gesture vocabularies (3–10 classes). Image-based deep models (e.g., GViT) reach about 96–98% in harder settings such as long range. No study was found that compares rule-based and learned classifiers on the same robot task, so a v1 (rules) vs v2 (learned) ablation would be a useful contribution.

### Cited Findings
- LSTM on MediaPipe landmarks for one-hand mobile-manipulator teleoperation: 100% on 3 gestures [S] — [J-STAGE](https://www.jstage.jst.go.jp/article/jciftomm/7/0/7_178/_article/-char/en)
- LSTM + fully connected classifier on MediaPipe Holistic landmarks for safe multimodal HRC (arXiv 2308.03690); accuracy not in the snippet [S] — [arXiv](https://arxiv.org/pdf/2308.03690)
- Raw 21-landmark sequences (125 timesteps) with a light RNN significantly beat engineered features (Gil-Martín et al., SCITEPRESS 2025) [S] — [SCITEPRESS](https://scitepress.org/Papers/2025/130535/130535.pdf)
- Landmark-based recognition sends much less data than images; about 98% on a small dataset (UPM 2023) [S] — [UPM](https://oa.upm.es/84969/)
- Image-level GViT for ultra-range gestures: 98.1% on the test set, about 96% on the robot (Bamani et al.) [V] — [arXiv](https://arxiv.org/html/2311.15361v2)
- PointingNet (a learned regressor) cuts pointing-direction error from 26° (MediaPipe geometric) to 1.4°, an example of learned models beating geometric rules on landmarks [V] — [arXiv](https://arxiv.org/html/2307.02949)
- Surveys to cite for background:
  - Qi, Ma, Cui, Yu (2023), "Computer vision-based hand gesture recognition for human-robot interaction: a review", *Complex & Intelligent Systems* [S, DOI not verified] — [record](https://libmast.utm.my/Record/doaj.art-b09f729d1e9943a2a52e3e1f53a4628a)
  - Hussain et al., arXiv 2409.06503 (2024), a vision/depth gesture-recognition HRI review covering DL, RL and transfer learning [S] — [arXiv](https://arxiv.org/abs/2409.06503v1)
  - Foteinos et al., arXiv 2507.04465 (2025), a survey of DL visual hand-gesture recognition since 2021 (static, dynamic, continuous) [S] — [arXiv](https://arxiv.org/pdf/2507.04465v3)
  - Jalayer et al. (2026), *Robotics and Computer-Integrated Manufacturing*, a review of hand detection, segmentation and recognition in HRI that notes HRI-specific datasets are scarce [S] — [polimi](https://re.public.polimi.it/handle/11311/1296170)

### Inferences
- Accuracy figures from different papers are not comparable: different gesture sets, datasets, and often within-subject splits. Reviewers will expect leave-one-subject-out evaluation, confusion matrices, and per-frame and per-event false-trigger rates.
- For v2's tiny vocabulary (point/move vs pinch), a thresholded thumb-index distance with hysteresis may match a learned MLP. An ablation (rule vs MLP vs temporal model) would answer the question empirically.

### Gaps
- No head-to-head rule-based vs MLP/LSTM study on the same robot task was found.
- Survey DOIs were not verified.

## Q5. Standardized HRI evaluation protocols and metrics reviewers expect

### Takeaway
Reviewers will expect: (1) task metrics (completion time, selection accuracy/error rate, final position error, end-to-end latency); (2) SUS for usability and NASA-TLX for workload; (3) for the cursor component, an ISO 9241-9/-411 Fitts' law throughput test against a mouse baseline; and (4) a within-subjects design with N of about 12–20 and appropriate statistics. The comparable studies found here used N=12–20.

### Cited Findings
- Soukoreff & MacKenzie (2004), "Towards a standard for pointing device evaluation, perspectives on 27 years of Fitts' law research in HCI", *Int. J. Human-Computer Studies* 61:751–789, DOI 10.1016/j.ijhcs.2004.09.001 (DOI taken from a BibSonomy record) [S]. Gives seven recommendations supplementing ISO 9241-9. Throughput (bits/s) = ID_e / MT combines speed and accuracy; ISO-conforming throughputs rarely exceed about 5 bps. — [author page](https://www.yorku.ca/mack/ijhcs2004.html); [BibSonomy](https://bibsonomy.org/bibtex/2feed563f46cbe1a450749d474a3994b1/ji)
- Example Fitts protocol for mid-air selection: Dube et al. 2022 (N=12, throughput, movement time, error rate, target re-entries) [V] — [yorku](http://www.yorku.ca/mack/iss2022.html)
- Example selection-accuracy protocol in HRI: Kavousian et al. 2026 (N=20, 2×2 within-subjects, accuracy %, time, Likert) [V] — [arXiv](https://arxiv.org/abs/2604.06073)
- Example SUS/TLX values in gesture or MR robot control: a bare-hand MR mobile-robot teleoperation study reported mean SUS 82.75 and NASA-TLX 5.19/21 [S] — [Robotics (MDPI) 15(8):149](https://doi.org/10.3390/robotics15080149). A touchscreen-vs-joystick manipulator study (N=20) found TLX fell from 52 to 43 and completion time more than halved [S] — [arXiv 2608.06219](https://arxiv.org/pdf/2608.06219). A wearable-glove interface had 9% higher success than a joystick, with better extended NASA-TLX [S] — [arXiv 2410.15414](https://arxiv.org/pdf/2410.15414). A kinesthetic vs joystick vs gesture teaching study (N=8) found the joystick best on simple picking [S] — [arXiv 2605.28033](https://arxiv.org/abs/2605.28033).
- Baselines in comparable robot studies: tablet bird's-eye map (AR Point&Click) — [arXiv](https://arxiv.org/abs/2203.15219); joystick (above).

### Inferences
- Recommended v2 protocol:
  - Conditions: within-subjects, (a) webcam pinch-cursor vs (b) mouse click on the same overhead view, optionally (c) v1 rule-based direct-drive gestures.
  - Measures:
    - selection time, selection accuracy and false-select rate
    - robot final-position error (m), task completion time
    - end-to-end latency, broken down by pipeline stage
    - SUS, raw NASA-TLX, and optionally Fitts throughput from a separate ISO 9241-411 multidirectional tapping task
  - N ≥ 12.
- Report SUS against the commonly cited average of 68. That benchmark is not cited here (Bangor et al. 2008 / Sauro), so find a source before using it.

### Gaps
- Original SUS (Brooke 1996) and NASA-TLX (Hart & Staveland 1988) sources were not fetched in this session. They are canonical, but verify the details before citing.
- ISO 9241-411:2012 standard details were not verified from ISO pages.
