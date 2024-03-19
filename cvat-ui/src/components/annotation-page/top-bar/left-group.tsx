// Copyright (C) 2020-2022 Intel Corporation
// Copyright (C) 2023 CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { Col } from 'antd/lib/grid';
import Icon, { StopOutlined, CheckCircleOutlined, LoadingOutlined } from '@ant-design/icons';
import Modal from 'antd/lib/modal';
import Button from 'antd/lib/button';
import Text from 'antd/lib/typography/Text';
import Dropdown from 'antd/lib/dropdown';
import Timeline from 'antd/lib/timeline/Timeline';

import AnnotationMenuContainer from 'containers/annotation-page/top-bar/annotation-menu';
import {
    MainMenuIcon, UndoIcon, RedoIcon, ChecklistIcon,
} from 'icons';
import { ActiveControl, ToolsBlockerState } from 'reducers';
import CVATTooltip from 'components/common/cvat-tooltip';
import customizableComponents from 'components/customizable-components';

interface Props {
    saving: boolean;
    undoAction?: string;
    redoAction?: string;
    undoShortcut: string;
    redoShortcut: string;
    drawShortcut: string;
    switchToolsBlockerShortcut: string;
    toolsBlockerState: ToolsBlockerState;
    activeControl: ActiveControl;
    onSaveAnnotation(): void;
    onUndoClick(): void;
    onRedoClick(): void;
    onFinishDraw(): void;
    onSwitchToolsBlockerState(): void;
    validateAnnotations(): Promise<any>;
}

function LeftGroup(props: Props): JSX.Element {
    const {
        saving,
        undoAction,
        redoAction,
        undoShortcut,
        redoShortcut,
        drawShortcut,
        switchToolsBlockerShortcut,
        activeControl,
        toolsBlockerState,
        onSaveAnnotation,
        onUndoClick,
        onRedoClick,
        onFinishDraw,
        onSwitchToolsBlockerState,
        validateAnnotations,
    } = props;

    const includesDoneButton = [
        ActiveControl.DRAW_POLYGON,
        ActiveControl.DRAW_POLYLINE,
        ActiveControl.DRAW_POINTS,
        ActiveControl.AI_TOOLS,
        ActiveControl.OPENCV_TOOLS,
    ].includes(activeControl);

    const includesToolsBlockerButton =
        [ActiveControl.OPENCV_TOOLS, ActiveControl.AI_TOOLS].includes(activeControl) && toolsBlockerState.buttonVisible;

    const shouldEnableToolsBlockerOnClick = [ActiveControl.OPENCV_TOOLS].includes(activeControl);
    const SaveButtonComponent = customizableComponents.SAVE_ANNOTATION_BUTTON;

    const [resultModalVisibility, setResultModalVisibility] = React.useState(false);
    const [results, setResults] = React.useState(null);

    const closeResultModal = (): void => {
        setResultModalVisibility(false);
    };

    const baseProps = {
        cancelButtonProps: { style: { display: 'none' } },
        okButtonProps: { style: { width: 100 } },
        onOk: closeResultModal,
        width: 1280,
        closable: false,
    };

    return (
        <>
            <Modal className='cvat-saving-job-modal' title='Saving changes on the server' visible={saving} footer={[]} closable={false}>
                <Text>CVAT is saving your annotations, please wait </Text>
                <LoadingOutlined />
            </Modal>
            <Modal title='Checking annotations for the current job' visible={resultModalVisibility} {...baseProps}>
                {resultModalVisibility && (
                    <Timeline>
                        {Object.keys(results as any).length === 0 ? (
                            <Timeline.Item>✅ Good Job. All annotations are correct.</Timeline.Item>
                        ) :
                            (Object.keys(results as any).map((check_no) => (
                                <>
                                    {/* eslint-disable-next-line react/jsx-one-expression-per-line */}
                                    <Timeline.Item key={check_no}>{(results as any)[check_no].passed ? '✅' : '❌' }&emsp;<b>{(results as any)[check_no].name}</b> {(results as any)[check_no].failureMessage}</Timeline.Item>
                                    {!(results as any)[check_no].passed && (
                                        (results as any)[check_no].images.map((image: any) => (
                                            <Timeline.Item style={{ marginLeft: '4%' }}>
                                                {image.passed ?
                                                    `✅  Frame ID: ${image.frame_id}` :
                                                    `❌  Frame ID: ${image.frame_id}${image.message ? ` => ${image.message}` : ''}` }
                                            </Timeline.Item>
                                        )))}
                                </>
                            )))}
                    </Timeline>
                )}
            </Modal>
            <Col className='cvat-annotation-header-left-group'>
                <Dropdown overlay={<AnnotationMenuContainer />}>
                    <Button type='link' className='cvat-annotation-header-menu-button cvat-annotation-header-button'>
                        <Icon component={MainMenuIcon} />
                        Menu
                    </Button>
                </Dropdown>
                <SaveButtonComponent
                    isSaving={saving}
                    onClick={saving ? undefined : onSaveAnnotation}
                    type='link'
                    className={saving ? 'cvat-annotation-header-save-button cvat-annotation-disabled-header-button' :
                        'cvat-annotation-header-save-button cvat-annotation-header-button'}
                />
                <CVATTooltip overlay={`Undo: ${undoAction} ${undoShortcut}`}>
                    <Button
                        style={{ pointerEvents: undoAction ? 'initial' : 'none', opacity: undoAction ? 1 : 0.5 }}
                        type='link'
                        className='cvat-annotation-header-undo-button cvat-annotation-header-button'
                        onClick={onUndoClick}
                    >
                        <Icon component={UndoIcon} />
                        <span>Undo</span>
                    </Button>
                </CVATTooltip>
                <CVATTooltip overlay={`Redo: ${redoAction} ${redoShortcut}`}>
                    <Button
                        style={{ pointerEvents: redoAction ? 'initial' : 'none', opacity: redoAction ? 1 : 0.5 }}
                        type='link'
                        className='cvat-annotation-header-redo-button cvat-annotation-header-button'
                        onClick={onRedoClick}
                    >
                        <Icon component={RedoIcon} />
                        Redo
                    </Button>
                </CVATTooltip>
                {includesDoneButton ? (
                    <CVATTooltip overlay={`Press "${drawShortcut}" to finish`}>
                        <Button type='link' className='cvat-annotation-header-done-button cvat-annotation-header-button' onClick={onFinishDraw}>
                            <CheckCircleOutlined />
                            Done
                        </Button>
                    </CVATTooltip>
                ) : (
                    <CVATTooltip overlay='Validate Annotations'>
                        <Button
                            type='link'
                            className='cvat-annotation-header-button'
                            onClick={() => {
                                validateAnnotations().then((res) => {
                                    setResults(res);
                                    setResultModalVisibility(true);
                                });
                            }}
                        >
                            <Icon component={ChecklistIcon} />
                            Check
                        </Button>
                    </CVATTooltip>
                )}
                {includesToolsBlockerButton ? (
                    <CVATTooltip overlay={`Press "${switchToolsBlockerShortcut}" to postpone running the algorithm `}>
                        <Button
                            type='link'
                            className={`cvat-annotation-header-block-tool-button cvat-annotation-header-button ${
                                toolsBlockerState.algorithmsLocked ? 'cvat-button-active' : ''
                            }`}
                            onClick={shouldEnableToolsBlockerOnClick ? onSwitchToolsBlockerState : undefined}
                        >
                            <StopOutlined />
                            Block
                        </Button>
                    </CVATTooltip>
                ) : null}
            </Col>
        </>
    );
}

export default React.memo(LeftGroup);
