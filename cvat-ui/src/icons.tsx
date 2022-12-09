// Copyright (C) 2020-2022 Intel Corporation
// Copyright (C) 2022 CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import React from 'react';

import SVGCVATLogo from './assets/cvat-logo.svg';
import SVGCursorIcon from './assets/cursor-icon.svg';
import SVGMoveIcon from './assets/move-icon.svg';
import SVGRotateIcon from './assets/rotate-icon.svg';
import SVGFitIcon from './assets/fit-to-window-icon.svg';
import SVGZoomIcon from './assets/zoom-icon.svg';
import SVGRectangleIcon from './assets/rectangle-icon.svg';
import SVGPolygonIcon from './assets/polygon-icon.svg';
import SVGPointIcon from './assets/point-icon.svg';
import SVGEllipseIcon from './assets/ellipse-icon.svg';
import SVGPolylineIcon from './assets/polyline-icon.svg';
import SVGTagIcon from './assets/tag-icon.svg';
import SVGMergeIcon from './assets/merge-icon.svg';
import SVGGroupIcon from './assets/group-icon.svg';
import SVGSplitIcon from './assets/split-icon.svg';
import SVGMainMenuIcon from './assets/main-menu-icon.svg';
import SVGSaveIcon from './assets/save-icon.svg';
import SVGUndoIcon from './assets/undo-icon.svg';
import SVGRedoIcon from './assets/redo-icon.svg';
import SVGFirstIcon from './assets/first-icon.svg';
import SVGBackJumpIcon from './assets/back-jump-icon.svg';
import SVGPreviousIcon from './assets/previous-icon.svg';
import SVGPreviousFilteredIcon from './assets/previous-filtered-icon.svg';
import SVGPreviousEmptyIcon from './assets/previous-empty-icon.svg';
import SVGPlayIcon from './assets/play-icon.svg';
import SVGPauseIcon from './assets/pause-icon.svg';
import SVGNextIcon from './assets/next-icon.svg';
import SVGNextFilteredIcon from './assets/next-filtered-icon.svg';
import SVGNextEmptyIcon from './assets/next-empty-icon.svg';
import SVGForwardJumpIcon from './assets/forward-jump-icon.svg';
import SVGLastIcon from './assets/last-icon.svg';
import SVGInfoIcon from './assets/info-icon.svg';
import SVGFullscreenIcon from './assets/fullscreen-icon.svg';
import SVGObjectOutsideIcon from './assets/object-outside-icon.svg';
import SVGBackgroundIcon from './assets/background-icon.svg';
import SVGForegroundIcon from './assets/foreground-icon.svg';
import SVGCubeIcon from './assets/cube-icon.svg';
import SVGSkeletonIcon from './assets/skeleton-icon.svg';
import SVGResetPerspectiveIcon from './assets/reset-perspective.svg';
import SVGColorizeIcon from './assets/colorize-icon.svg';
import SVGAITools from './assets/ai-tools-icon.svg';
import SVGBrain from './assets/brain.svg';
import SVGOpenCV from './assets/opencv.svg';
import SVGFilterIcon from './assets/object-filter-icon.svg';
import SVGCVATAzureProvider from './assets/vscode-icons_file-type-azure.svg';
import SVGCVATS3Provider from './assets/S3.svg';
import SVGCVATGoogleCloudProvider from './assets/google-cloud.svg';
import SVGRestoreIcon from './assets/restore-icon.svg';
import SVGMultiPlusIcon from './assets/multi-plus-icon.svg';
import SVGUpgradeIcon from './assets/upgrade-icon.svg';

export const CVATLogo = React.memo((): JSX.Element => <SVGCVATLogo />);
export const CursorIcon = React.memo((): JSX.Element => <SVGCursorIcon />);
export const MoveIcon = React.memo((): JSX.Element => <SVGMoveIcon />);
export const RotateIcon = React.memo((): JSX.Element => <SVGRotateIcon />);
export const FitIcon = React.memo((): JSX.Element => <SVGFitIcon />);
export const ZoomIcon = React.memo((): JSX.Element => <SVGZoomIcon />);
export const RectangleIcon = React.memo((): JSX.Element => <SVGRectangleIcon />);
export const PolygonIcon = React.memo((): JSX.Element => <SVGPolygonIcon />);
export const PointIcon = React.memo((): JSX.Element => <SVGPointIcon />);
export const EllipseIcon = React.memo((): JSX.Element => <SVGEllipseIcon />);
export const PolylineIcon = React.memo((): JSX.Element => <SVGPolylineIcon />);
export const TagIcon = React.memo((): JSX.Element => <SVGTagIcon />);
export const MergeIcon = React.memo((): JSX.Element => <SVGMergeIcon />);
export const GroupIcon = React.memo((): JSX.Element => <SVGGroupIcon />);
export const SplitIcon = React.memo((): JSX.Element => <SVGSplitIcon />);
export const MainMenuIcon = React.memo((): JSX.Element => <SVGMainMenuIcon />);
export const SaveIcon = React.memo((): JSX.Element => <SVGSaveIcon />);
export const UndoIcon = React.memo((): JSX.Element => <SVGUndoIcon />);
export const RedoIcon = React.memo((): JSX.Element => <SVGRedoIcon />);
export const FirstIcon = React.memo((): JSX.Element => <SVGFirstIcon />);
export const BackJumpIcon = React.memo((): JSX.Element => <SVGBackJumpIcon />);
export const PreviousIcon = React.memo((): JSX.Element => <SVGPreviousIcon />);
export const PreviousFilteredIcon = React.memo((): JSX.Element => <SVGPreviousFilteredIcon />);
export const PreviousEmptyIcon = React.memo((): JSX.Element => <SVGPreviousEmptyIcon />);
export const PauseIcon = React.memo((): JSX.Element => <SVGPauseIcon />);
export const PlayIcon = React.memo((): JSX.Element => <SVGPlayIcon />);
export const NextIcon = React.memo((): JSX.Element => <SVGNextIcon />);
export const NextFilteredIcon = React.memo((): JSX.Element => <SVGNextFilteredIcon />);
export const NextEmptyIcon = React.memo((): JSX.Element => <SVGNextEmptyIcon />);
export const ForwardJumpIcon = React.memo((): JSX.Element => <SVGForwardJumpIcon />);
export const LastIcon = React.memo((): JSX.Element => <SVGLastIcon />);
export const InfoIcon = React.memo((): JSX.Element => <SVGInfoIcon />);
export const FullscreenIcon = React.memo((): JSX.Element => <SVGFullscreenIcon />);
export const ObjectOutsideIcon = React.memo((): JSX.Element => <SVGObjectOutsideIcon />);
export const BackgroundIcon = React.memo((): JSX.Element => <SVGBackgroundIcon />);
export const ForegroundIcon = React.memo((): JSX.Element => <SVGForegroundIcon />);
export const CubeIcon = React.memo((): JSX.Element => <SVGCubeIcon />);
export const SkeletonIcon = React.memo((): JSX.Element => <SVGSkeletonIcon />);
export const ResetPerspectiveIcon = React.memo((): JSX.Element => <SVGResetPerspectiveIcon />);
export const AIToolsIcon = React.memo((): JSX.Element => <SVGAITools />);
export const ColorizeIcon = React.memo((): JSX.Element => <SVGColorizeIcon />);
export const BrainIcon = React.memo((): JSX.Element => <SVGBrain />);
export const OpenCVIcon = React.memo((): JSX.Element => <SVGOpenCV />);
export const FilterIcon = React.memo((): JSX.Element => <SVGFilterIcon />);
export const AzureProvider = React.memo((): JSX.Element => <SVGCVATAzureProvider />);
export const S3Provider = React.memo((): JSX.Element => <SVGCVATS3Provider />);
export const GoogleCloudProvider = React.memo((): JSX.Element => <SVGCVATGoogleCloudProvider />);
export const RestoreIcon = React.memo((): JSX.Element => <SVGRestoreIcon />);
export const MutliPlusIcon = React.memo((): JSX.Element => <SVGMultiPlusIcon />);
export const UpgradeIcon = React.memo((): JSX.Element => <SVGUpgradeIcon />);
