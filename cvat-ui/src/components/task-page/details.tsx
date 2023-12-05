// Copyright (C) 2019-2022 Intel Corporation
// Copyright (C) 2022-2023 CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { connect } from 'react-redux';

import { Row, Col } from 'antd/lib/grid';
import Text from 'antd/lib/typography/Text';
import Title from 'antd/lib/typography/Title';
import { Button } from 'antd';
import notification from 'antd/lib/notification';
import moment from 'moment';

import { getCore, Task, User } from 'cvat-core-wrapper';
import AutomaticAnnotationProgress from 'components/tasks-page/automatic-annotation-progress';
import MdGuideControl from 'components/md-guide/md-guide-control';
import Preview from 'components/common/preview';
import { cancelInferenceAsync } from 'actions/models-actions';
import { CombinedState, ActiveInference } from 'reducers';
import { sendRequest } from 'trisetra-api-wrapper';
import UserSelector from './user-selector';
import BugTrackerEditor from './bug-tracker-editor';
import LabelsEditorComponent from '../labels-editor/labels-editor';
import ProjectSubsetField from '../create-task-page/project-subset-field';
import { PLYRenderer } from './ply-renderer';

interface OwnProps {
    task: Task;
    onUpdateTask: (task: Task) => Promise<void>;
}

interface StateToProps {
    activeInference: ActiveInference | null;
    projectSubsets: string[];
    dumpers: any[];
    user: any;
}

interface DispatchToProps {
    cancelAutoAnnotation(): void;
}

function mapStateToProps(state: CombinedState, own: OwnProps): StateToProps & OwnProps {
    const [taskProject] = state.projects.current.filter((project) => project.id === own.task.projectId);

    return {
        ...own,
        dumpers: state.formats.annotationFormats.dumpers,
        user: state.auth.user,
        activeInference: state.models.inferences[own.task.id] || null,
        projectSubsets: taskProject ?
            ([
                ...new Set(taskProject.subsets),
            ] as string[]) :
            [],
    };
}

function mapDispatchToProps(dispatch: any, own: OwnProps): DispatchToProps {
    return {
        cancelAutoAnnotation(): void {
            dispatch(cancelInferenceAsync(own.task.id));
        },
    };
}

const core = getCore();

interface State {
    name: string;
    subset: string;
    plyFile: string;
    lastModified: string;
}

const enum WorkOrderStatus {
    CREATED = 'created',
    UPLOADED_TO_CVAT = 'uploaded_to_cvat',
    ANNOTATED = 'annotated',
    COMPLETED = 'completed',
    FAILED = 'failed',
    REQUIRE_INPUT = 'require_input',
}

type Props = DispatchToProps & StateToProps & OwnProps;

class DetailsComponent extends React.PureComponent<Props, State> {
    private reconstructionWrapperRef: React.RefObject<HTMLDivElement>;
    private workOrderDetailsWrapperRef: React.RefObject<HTMLDivElement>;
    private workOderDetailsElement: HTMLParagraphElement;

    constructor(props: Props) {
        super(props);
        const { task: taskInstance } = props;
        this.state = {
            name: taskInstance.name,
            subset: taskInstance.subset,
            plyFile: '',
            lastModified: '',
        };
        this.reconstructionWrapperRef = React.createRef<HTMLDivElement>();
        this.workOderDetailsElement = document.createElement('p');
        this.workOrderDetailsWrapperRef = React.createRef<HTMLDivElement>();
    }

    public componentDidUpdate(prevProps: Props): void {
        const { task: taskInstance } = this.props;
        const { reconstructionWrapperRef } = this;

        if (prevProps !== this.props) {
            this.setState({
                name: taskInstance.name,
            });

            sendRequest(`tasks/${taskInstance.id}/reconstruction-previews`).then((res) => {
                if (res.previews.length > 0) {
                    res.previews.forEach((preview: string) => {
                        if (preview.includes('.ply')) {
                            this.setState({ plyFile: preview, lastModified: res.last_modified });
                        } else {
                            const img = new Image();
                            img.onload = () => {
                                const { height, width } = img;
                                if (width > height) {
                                    img.style.width = '100%';
                                } else {
                                    img.style.height = '100%';
                                }
                            };
                            const imgName = preview.substring(preview.lastIndexOf('/') + 1, preview.indexOf('?'));
                            // eslint-disable-next-line security/detect-non-literal-fs-filename
                            img.onclick = () => window.open(
                                imgName === 'combined_room_camera_geometry_preview.png' ?
                                    `https://www.trisetra.com/panorama/?source=${window.location.href}&url=${preview}` :
                                    preview,
                            );
                            img.loading = 'lazy';
                            img.src = preview;
                            img.alt = `Could not load ${imgName}`;
                            reconstructionWrapperRef.current?.appendChild(img);
                        }
                    });
                } else {
                    const img = new Image();
                    img.src = '';
                    img.alt = res.message;
                    reconstructionWrapperRef.current?.appendChild(img);
                }
            }).catch((err) => {
                const img = new Image();
                img.src = '';
                img.alt = err.message;
                reconstructionWrapperRef.current?.appendChild(img);
            });

            this.fetchWorkOrderStatus();
        }
    }

    private fetchWorkOrderStatus(): void {
        const { task: taskInstance } = this.props;
        const { workOrderDetailsWrapperRef, workOderDetailsElement } = this;
        sendRequest(`tasks/${taskInstance.id}`).then((data) => {
            const workOrder = data?.work_order;
            workOderDetailsElement.textContent = workOrder ? `Work order status: ${workOrder.status}` : data?.message;
            workOrderDetailsWrapperRef.current?.appendChild(workOderDetailsElement);
        }).catch((error) => {
            console.log(error);
            workOderDetailsElement.textContent = 'Failed to Fetch Work Order Status';
            workOrderDetailsWrapperRef.current?.appendChild(workOderDetailsElement);
        });
    }

    private updateReconstructionStatus(status: WorkOrderStatus, notify = false, helpText: string | undefined = ''): void {
        const { task: taskInstance } = this.props;
        sendRequest(`tasks/${taskInstance.id}/status/${status}`, {
            query: { notify: `${notify}`, helpText },
        }).then(() => {
            notification.success({
                message: 'Work order updated',
                description: `Work Order status set to: ${status}`,
            });
        }).catch(() => {
            notification.error({
                message: 'Could not update reconstruction status',
                description: 'An Error occurred while updating reconstruction status',
            });
        }).finally(() => {
            this.fetchWorkOrderStatus();
        });
    }

    private renderReconstructionThumbnail(): JSX.Element {
        const { reconstructionWrapperRef, workOrderDetailsWrapperRef } = this;
        const { plyFile, lastModified } = this.state;

        return (
            <Row>
                <Col span={12}>
                    <div
                        ref={reconstructionWrapperRef}
                        style={{
                            height: 'auto',
                            width: 'auto',
                            maxWidth: '100%',
                            maxHeight: '100%',
                            minHeight: '300px',
                            minWidth: '40%',
                            color: 'red',
                        }}
                    />
                </Col>
                <Col span={12}>
                    <Row style={{ alignItems: 'center', display: 'flex', justifyContent: 'center' }}>
                        <div ref={workOrderDetailsWrapperRef} />
                    </Row>
                    <Row style={{ alignItems: 'center', display: 'flex', justifyContent: 'center' }}>
                        <Button onClick={() => this.updateReconstructionStatus(WorkOrderStatus.COMPLETED)}>
                            Finalize
                        </Button>
                        <Button onClick={() => this.updateReconstructionStatus(WorkOrderStatus.COMPLETED, true)}>
                            Finalize and Notify
                        </Button>
                        <Button onClick={async () => {
                            // eslint-disable-next-line no-alert
                            const helpText = prompt('Please enter a reason for requiring additional input');
                            this.updateReconstructionStatus(WorkOrderStatus.REQUIRE_INPUT, true, helpText);
                        }}
                        >
                            Require Additional Input
                        </Button>
                        <Button onClick={async () => this.updateReconstructionStatus(WorkOrderStatus.FAILED, true)}>
                            Failed
                        </Button>
                    </Row>
                    {plyFile && lastModified && <PLYRenderer lastModified={lastModified} plyFile={plyFile} />}
                </Col>
            </Row>
        );
    }

    private renderTaskName(): JSX.Element {
        const { name } = this.state;
        const { task: taskInstance, onUpdateTask } = this.props;

        return (
            <Title level={4}>
                <Text
                    editable={{
                        onChange: (value: string): void => {
                            this.setState({
                                name: value,
                            });

                            taskInstance.name = value;
                            onUpdateTask(taskInstance);
                        },
                    }}
                    className='cvat-text-color'
                >
                    {name}
                </Text>
            </Title>
        );
    }

    private renderDescription(): JSX.Element {
        const { task: taskInstance, onUpdateTask } = this.props;
        const owner = taskInstance.owner ? taskInstance.owner.username : null;
        const assignee = taskInstance.assignee ? taskInstance.assignee : null;
        const created = moment(taskInstance.createdDate).format('MMMM Do YYYY');
        const assigneeSelect = (
            <UserSelector
                value={assignee}
                onSelect={(value: User | null): void => {
                    if (taskInstance?.assignee?.id === value?.id) return;
                    taskInstance.assignee = value;
                    onUpdateTask(taskInstance);
                }}
            />
        );

        return (
            <Row className='cvat-task-details-user-block' justify='space-between' align='middle'>
                <Col span={12}>
                    {owner && (
                        <Text type='secondary'>{`Task #${taskInstance.id} Created by ${owner} on ${created}`}</Text>
                    )}
                </Col>
                <Col>
                    <Text type='secondary'>Assigned to</Text>
                    {assigneeSelect}
                </Col>
            </Row>
        );
    }

    private renderLabelsEditor(): JSX.Element {
        const { task: taskInstance, onUpdateTask } = this.props;

        return (
            <Row>
                <Col span={24}>
                    <LabelsEditorComponent
                        labels={taskInstance.labels.map((label: any): string => label.toJSON())}
                        onSubmit={(labels: any[]): void => {
                            taskInstance.labels = labels.map((labelData): any => new core.classes.Label(labelData));
                            onUpdateTask(taskInstance);
                        }}
                    />
                </Col>
            </Row>
        );
    }

    private renderSubsetField(): JSX.Element {
        const { subset } = this.state;
        const {
            task: taskInstance,
            projectSubsets,
            onUpdateTask,
        } = this.props;

        return (
            <Row>
                <Col span={24}>
                    <Text className='cvat-text-color'>Subset:</Text>
                </Col>
                <Col span={24}>
                    <ProjectSubsetField
                        value={subset}
                        projectId={taskInstance.projectId as number}
                        projectSubsets={projectSubsets}
                        onChange={(value) => {
                            this.setState({
                                subset: value,
                            });

                            if (taskInstance.subset !== value) {
                                taskInstance.subset = value;
                                onUpdateTask(taskInstance);
                            }
                        }}
                    />
                </Col>
            </Row>
        );
    }

    public render(): JSX.Element {
        const {
            activeInference,
            task: taskInstance,
            cancelAutoAnnotation,
            onUpdateTask,
        } = this.props;

        return (
            <div className='cvat-task-details'>
                <Row justify='start' align='middle'>
                    <Col className='cvat-task-details-task-name'>{this.renderTaskName()}</Col>
                </Row>
                <Row justify='space-between' align='top'>
                    <Col md={8} lg={7} xl={7} xxl={6}>
                        <Row justify='start' align='middle'>
                            <Col span={24}>
                                <Preview
                                    task={taskInstance}
                                    loadingClassName='cvat-task-item-loading-preview'
                                    emptyPreviewClassName='cvat-task-item-empty-preview'
                                    previewClassName='cvat-task-item-preview'
                                    showQAIcon
                                />
                            </Col>
                        </Row>
                    </Col>
                    <Col md={16} lg={17} xl={17} xxl={18}>
                        {this.renderDescription()}
                        { taskInstance.projectId === null && <MdGuideControl instanceType='task' id={taskInstance.id} /> }
                        <Row justify='space-between' align='middle'>
                            <Col span={12}>
                                <BugTrackerEditor
                                    instance={taskInstance}
                                    onChange={(bugTracker) => {
                                        taskInstance.bugTracker = bugTracker;
                                        onUpdateTask(taskInstance);
                                    }}
                                />
                            </Col>
                            <Col span={10}>
                                <AutomaticAnnotationProgress
                                    activeInference={activeInference}
                                    cancelAutoAnnotation={cancelAutoAnnotation}
                                />
                            </Col>
                        </Row>
                        {!taskInstance.projectId && this.renderLabelsEditor()}
                        {taskInstance.projectId && this.renderSubsetField()}
                    </Col>
                    {this.renderReconstructionThumbnail()}
                </Row>
            </div>
        );
    }
}

export default connect(mapStateToProps, mapDispatchToProps)(DetailsComponent);
