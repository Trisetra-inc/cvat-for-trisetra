// Copyright (C) 2020-2022 Intel Corporation
// Copyright (C) 2022 CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import './styles.scss';
import React, { useCallback } from 'react';
import Menu from 'antd/lib/menu';
import Modal from 'antd/lib/modal';
import { LoadingOutlined } from '@ant-design/icons';
// eslint-disable-next-line import/no-extraneous-dependencies
import { MenuInfo } from 'rc-menu/lib/interface';
import { DimensionType } from 'cvat-core-wrapper';
import { usePlugins } from 'utils/hooks';
import { CombinedState } from 'reducers';
import { sendRequest, TRISETRA_API_ENDPOINT, TRISETRA_API_TOKEN } from 'trisetra-api-wrapper';

interface Props {
    taskID: number;
    projectID: number | null;
    taskMode: string;
    bugTracker: string;
    loaders: any[];
    dumpers: any[];
    inferenceIsActive: boolean;
    taskDimension: DimensionType;
    backupIsActive: boolean;
    onClickMenu: (params: MenuInfo) => void;
}

export enum Actions {
    LOAD_TASK_ANNO = 'load_task_anno',
    EXPORT_TASK_DATASET = 'export_task_dataset',
    EXPORT_TASK_ANNOTATIONS = 'export_task_annotations',
    GENERATE_BLEND_AND_PREVIEW = 'generate_blend_and_preview',
    GENERATE_GLB_AND_HDRS = 'generate_glb_and_hdrs',
    DELETE_TASK = 'delete_task',
    RUN_AUTO_ANNOTATION = 'run_auto_annotation',
    MOVE_TASK_TO_PROJECT = 'move_task_to_project',
    OPEN_BUG_TRACKER = 'open_bug_tracker',
    BACKUP_TASK = 'backup_task',
    VIEW_ANALYTICS = 'view_analytics',
}

function ActionsMenuComponent(props: Props): JSX.Element {
    const {
        taskID,
        projectID,
        bugTracker,
        inferenceIsActive,
        backupIsActive,
        onClickMenu,
    } = props;

    const plugins = usePlugins((state: CombinedState) => state.plugins.components.taskActions.items, props);

    const onClickMenuWrapper = useCallback(
        (params: MenuInfo) => {
            if (!params) {
                return;
            }

            if (params.key === Actions.DELETE_TASK) {
                Modal.confirm({
                    title: `The task ${taskID} will be deleted`,
                    content: 'All related data (images, annotations) will be lost. Continue?',
                    className: 'cvat-modal-confirm-delete-task',
                    onOk: () => {
                        onClickMenu(params);
                    },
                    okButtonProps: {
                        type: 'primary',
                        danger: true,
                    },
                    okText: 'Delete',
                });
            } else if (params.key === Actions.EXPORT_TASK_ANNOTATIONS) {
                const frameRotationInfo: string[] = [];
                Object.keys(localStorage)
                    .filter((key: string) => key.startsWith(`Task_${taskID}_Job_`) && key.endsWith('_rotation'))
                    .forEach((key: string) => {
                        const rotationValue = Number(localStorage.getItem(key));
                        const anticlockWiseRotation =
                            rotationValue > 0 ? (4 - rotationValue) * 90 : rotationValue * -90;
                        frameRotationInfo.push(`${key.split('_').at(-2)}=${anticlockWiseRotation}`);
                    });
                const exportUrl = `${TRISETRA_API_ENDPOINT}/annotations/${taskID}/export?token=${TRISETRA_API_TOKEN}&${frameRotationInfo.join('&')}`;
                const exportTab = window.open(exportUrl, '_blank', 'noopener noreferrer');
                exportTab?.focus();
            } else if ([Actions.GENERATE_BLEND_AND_PREVIEW, Actions.GENERATE_GLB_AND_HDRS].includes(params.key)) {
                const path = `tasks/${taskID}/${params.key === Actions.GENERATE_BLEND_AND_PREVIEW ? 'generate-blend' : 'generate-glb'}`;
                sendRequest(path).then((data) => {
                    Modal.success({
                        title: 'Request sent',
                        content: data.message,
                    });
                    if (data.redirect_url) {
                        const redirectedTab = window.open(data.redirect_url, '_blank', 'noopener noreferrer');
                        redirectedTab?.focus();
                    }
                }).catch((err) => {
                    Modal.error({
                        title: 'Error',
                        content: err.message,
                    });
                });
            } else {
                onClickMenu(params);
            }
        },
        [taskID],
    );

    const menuItems: [JSX.Element, number][] = [];
    menuItems.push([(
        <Menu.Item key={Actions.LOAD_TASK_ANNO}>Upload annotations</Menu.Item>
    ), 0]);

    menuItems.push([(
        <Menu.Item key={Actions.EXPORT_TASK_DATASET}>Export task dataset</Menu.Item>
    ), 10]);

    menuItems.push([(
        <Menu.Item key={Actions.EXPORT_TASK_ANNOTATIONS}>Export Annotations & Reconstruct</Menu.Item>
    ), 11]);

    menuItems.push([(
        <Menu.Item key={Actions.GENERATE_BLEND_AND_PREVIEW}>Generate Preview & Blend File</Menu.Item>
    ), 12]);

    menuItems.push([(
        <Menu.Item key={Actions.GENERATE_GLB_AND_HDRS}>Generate & Upload GLB + HDRs</Menu.Item>
    ), 13]);

    if (bugTracker) {
        menuItems.push([(
            <Menu.Item key={Actions.OPEN_BUG_TRACKER}>Open bug tracker</Menu.Item>
        ), 20]);
    }

    menuItems.push([(
        <Menu.Item disabled={inferenceIsActive} key={Actions.RUN_AUTO_ANNOTATION}>
            Automatic annotation
        </Menu.Item>
    ), 30]);

    menuItems.push([(
        <Menu.Item
            key={Actions.BACKUP_TASK}
            disabled={backupIsActive}
            icon={backupIsActive && <LoadingOutlined id='cvat-backup-task-loading' />}
        >
            Backup Task
        </Menu.Item>
    ), 40]);

    menuItems.push([(
        <Menu.Item
            key={Actions.VIEW_ANALYTICS}
        >
            View analytics
        </Menu.Item>
    ), 50]);

    if (projectID === null) {
        menuItems.push([(
            <Menu.Item key={Actions.MOVE_TASK_TO_PROJECT}>Move to project</Menu.Item>
        ), 60]);
    }

    menuItems.push([(
        <React.Fragment key={Actions.DELETE_TASK}>
            <Menu.Divider />
            <Menu.Item key={Actions.DELETE_TASK}>Delete</Menu.Item>
        </React.Fragment>
    ), 70]);

    menuItems.push(
        ...plugins.map(({ component: Component, weight }, index) => {
            const menuItem = Component({ key: index, targetProps: props });
            return [menuItem, weight] as [JSX.Element, number];
        }),
    );

    return (
        <Menu selectable={false} className='cvat-actions-menu' onClick={onClickMenuWrapper}>
            { menuItems.sort((menuItem1, menuItem2) => menuItem1[1] - menuItem2[1])
                .map((menuItem) => menuItem[0]) }
        </Menu>
    );
}

export default React.memo(ActionsMenuComponent);
